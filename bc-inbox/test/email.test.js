const test = require('node:test');
const assert = require('node:assert');
const { isReleaseSubject, parseReleaseEmail, mergeItems, bodiesFromPayload, headerValue, padBase64 } = require('../Parse.js');
const fixtures = require('./fixtures/emails.json');

// Fixtures are real Bandcamp emails to mfyn@ (Oct-Nov 2026), trimmed.
for (const f of fixtures) {
  test(`email: ${f.name}`, () => {
    const item = parseReleaseEmail(f);
    if (f.expect === null) {
      assert.strictEqual(isReleaseSubject(f.subject), false);
      assert.strictEqual(item, null);
      return;
    }
    assert.ok(item, 'expected a release');
    for (const [k, v] of Object.entries(f.expect)) assert.strictEqual(item[k], v, k);
    assert.strictEqual(item.date, f.date);
    assert.strictEqual(item.source, 'email');
    assert.strictEqual(item.status, 'queued');
  });
}

test('title with quotes inside', () => {
  const item = parseReleaseEmail({
    subject: 'New release from X', date: 'd',
    plain: 'X just released "Play "Some" Music" by Y, check it out at:\n\nhttps://x.bandcamp.com/album/play?from=a'
  });
  assert.strictEqual(item.title, 'Play "Some" Music');
  assert.strictEqual(item.artist, 'Y');
});

test('mergeItems dedupes by release URL and sorts newest first', () => {
  const a = { releaseUrl: 'u1', date: '2026-11-01T00:00:00Z', from: 'a' };
  const b = { releaseUrl: 'u1', date: '2026-11-05T00:00:00Z', from: 'b' };
  const c = { releaseUrl: 'u2', date: '2026-11-03T00:00:00Z' };
  const out = mergeItems([[a], [b, c]]);
  assert.deepStrictEqual(out.map(i => i.releaseUrl), ['u2', 'u1']);
  assert.strictEqual(out[1].from, 'a');
});

test('bodiesFromPayload reads nested multipart parts', () => {
  const enc = s => Buffer.from(s, 'utf8').toString('base64url');
  const payload = {
    mimeType: 'multipart/mixed',
    headers: [{ name: 'Subject', value: 'New release from Z' }],
    parts: [{ mimeType: 'multipart/alternative', parts: [
      { mimeType: 'text/plain', body: { data: enc('plain “text”') } },
      { mimeType: 'text/html', body: { data: enc('<b>html</b>') } }
    ] }]
  };
  const out = bodiesFromPayload(payload, d => Buffer.from(d, 'base64url').toString('utf8'));
  assert.deepStrictEqual(out, { plain: 'plain “text”', html: '<b>html</b>' });
  assert.strictEqual(headerValue(payload, 'subject'), 'New release from Z');
});

test('padBase64 restores the padding Gmail leaves off', () => {
  assert.strictEqual(padBase64('YQ'), 'YQ==');
  assert.strictEqual(padBase64('YWI'), 'YWI=');
  assert.strictEqual(padBase64('YWJj'), 'YWJj');
  assert.strictEqual(padBase64('YW\nJj'), 'YWJj');
});
