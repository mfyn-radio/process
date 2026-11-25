const test = require('node:test');
const assert = require('node:assert');
const { normalizeReleaseUrl, parseReleasePage, embedUrl } = require('../Parse.js');

test('normalizes release links', () => {
  assert.strictEqual(
    normalizeReleaseUrl('https://LustTapes.bandcamp.com/album/Sociopathic-Morbid-Aberrations?from=fanpub_fnb#x'),
    'https://lusttapes.bandcamp.com/album/sociopathic-morbid-aberrations');
  assert.strictEqual(normalizeReleaseUrl('https://x.bandcamp.com/track/a-b'), 'https://x.bandcamp.com/track/a-b');
  assert.strictEqual(normalizeReleaseUrl('https://x.bandcamp.com/'), null);
  assert.strictEqual(normalizeReleaseUrl('https://x.bandcamp.com/merch/tee'), null);
});

const PAGE = `
<meta name="bc-page-properties" content="{&quot;item_type&quot;:&quot;a&quot;,&quot;item_id&quot;:1234567890,&quot;tralbum_page_version&quot;:0}">
<meta property="og:title" content="Sociopathic Morbid Aberrations, by Corpse Splitter">
<meta property="og:video" content="https://bandcamp.com/EmbeddedPlayer/v=2/album=1234567890/size=large/tracklist=false/artwork=small/">
<p id="band-name-location"><span class="title">LUST TAPES</span>
<span class="location secondaryText">Rotterdam, Netherlands</span></p>`;

test('reads embed ID, artist, title and location', () => {
  const info = parseReleasePage(PAGE);
  assert.deepStrictEqual(info, {
    itemType: 'album', itemId: '1234567890', artist: 'Corpse Splitter',
    title: 'Sociopathic Morbid Aberrations', location: 'Rotterdam, Netherlands',
    pageName: 'LUST TAPES', tags: []
  });
  assert.strictEqual(embedUrl(info),
    'https://bandcamp.com/EmbeddedPlayer/album=1234567890/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/transparent=true/');
});

test('falls back to og:video for tracks', () => {
  const info = parseReleasePage('<meta property="og:video" content="https://bandcamp.com/EmbeddedPlayer/v=2/track=42/size=large/">');
  assert.strictEqual(info.itemType, 'track');
  assert.strictEqual(info.itemId, '42');
});

const { applyEnrichment } = require('../Parse.js');

const LABEL_PAGE = `
<meta property="og:title" content="Sociopathic Morbid Aberrations, by Corpse Splitter">
<meta name="bc-page-properties" content="{&quot;item_type&quot;:&quot;a&quot;,&quot;item_id&quot;:2765817689}">
<p id="band-name-location">
    <span class="title">LUST TAPES</span>
    <span class="location secondaryText">Amsterdam, Netherlands</span>
</p>
<a class="tag" href="https://bandcamp.com/discover/death-metal?from=tralbum">death metal</a>
<a class="tag" href="https://bandcamp.com/discover/goregrind?from=tralbum">goregrind</a>
<a class="tag" href="https://bandcamp.com/discover/amsterdam?from=tralbum">Amsterdam</a>`;

test('reads page owner and tags', () => {
  const info = parseReleasePage(LABEL_PAGE);
  assert.strictEqual(info.pageName, 'LUST TAPES');
  assert.strictEqual(info.location, 'Amsterdam, Netherlands');
  assert.deepStrictEqual(info.tags, ['death metal', 'goregrind', 'Amsterdam']);
  assert.strictEqual(info.itemId, '2765817689');
});

test('a label page gives a label location; the artist page gives a release location', () => {
  const base = { releaseUrl: 'u', artist: 'Corpse Splitter', title: 't', itemType: 'album' };
  const viaLabel = applyEnrichment(base, Object.assign(parseReleasePage(LABEL_PAGE), {}));
  assert.strictEqual(viaLabel.locationSource, 'label');
  assert.strictEqual(viaLabel.enriched, true);
  assert.ok(viaLabel.embedUrl.includes('album=2765817689'));

  const own = applyEnrichment({ releaseUrl: 'u', artist: 'Lust Tapes!' }, parseReleasePage(LABEL_PAGE));
  assert.strictEqual(own.locationSource, 'release');

  const none = applyEnrichment(base, { itemId: '1', itemType: 'album', location: null, pageName: 'X', tags: [] });
  assert.strictEqual(none.locationSource, 'unknown');

  const failed = applyEnrichment(base, { error: 'HTTP 404' });
  assert.strictEqual(failed.enriched, true);
  assert.strictEqual(failed.enrichError, 'HTTP 404');
  assert.strictEqual(base.enriched, undefined, 'input not changed');
});
