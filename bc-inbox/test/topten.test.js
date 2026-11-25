const test = require('node:test');
const assert = require('node:assert');
const P = require('../Parse.js');
global.normalizeReleaseUrl = P.normalizeReleaseUrl;
global.decodeEntities = P.decodeEntities;
const T = require('../TopTen.js');
const { queueOrder } = require('../Region.js');

const CSV = '﻿Artist, Location, Bandcamp URL, Suggested track, Tags, IG handle, IG followers, Fit notes, Rising notes, Next BeNe show, Contact\n' +
  'Crowd Of Chairs,"Ghent, Belgium",https://crowdofchairsband.bandcamp.com/track/comparison?from=x,Comparison,"noise rock, post-punk",@crowdofchairs,2100,"Wiry, loud; ""fits"" the punk block",Sold out Trix,"12 Dec, Ghent",\n' +
  'Some Artist,"Rotterdam, Netherlands",https://someartist.bandcamp.com/,Night Bus,ambient,,,,,,\n' +
  'No Link Band,Utrecht,,,,,,,,,\n';

test('parses the weekly CSV in ranked order, quotes and all', () => {
  const items = T.top10Items(CSV, '2026-11-24');
  assert.strictEqual(items.length, 3);
  assert.deepStrictEqual(items.map(i => i.top10Rank), [1, 2, 3]);
  const a = items[0];
  assert.strictEqual(a.releaseUrl, 'https://crowdofchairsband.bandcamp.com/track/comparison');
  assert.strictEqual(a.location, 'Ghent, Belgium');
  assert.strictEqual(a.locationSource, 'csv');
  assert.deepStrictEqual(a.tags, ['noise rock', 'post-punk']);
  assert.strictEqual(a.fitNotes, 'Wiry, loud; "fits" the punk block');
  assert.strictEqual(a.nextBeneShow, '12 Dec, Ghent');
  assert.strictEqual(a.source, 'top10');
  assert.strictEqual(items[1].releaseUrl, null);
  assert.strictEqual(items[1].linkKind, 'artist');
  assert.strictEqual(items[2].linkKind, null);
});

test('finds the newest rising-artists file by the date in its name', () => {
  const f = T.newestTop10File([
    { name: 'rising-artists-2026-11-17.csv', id: 'a' },
    { name: 'notes.txt', id: 'x' },
    { name: 'rising-artists-2026-11-24.csv', id: 'b' },
    { name: 'rising-artists-2026-11-24 (1).csv', id: 'c' }
  ]);
  assert.deepStrictEqual(f, { name: 'rising-artists-2026-11-24.csv', id: 'b', week: '2026-11-24' });
  assert.strictEqual(T.newestTop10File([{ name: 'other.csv' }]), null);
});

test('link kinds and slugs', () => {
  assert.strictEqual(T.linkKind('https://x.bandcamp.com'), 'artist');
  assert.strictEqual(T.linkKind('https://x.bandcamp.com/music'), 'artist');
  assert.strictEqual(T.linkKind('https://x.bandcamp.com/album/y'), 'release');
  assert.strictEqual(T.linkKind('https://x.bandcamp.com/merch'), null);
  assert.strictEqual(T.slugify('Night Bus (Edit)'), 'night-bus-edit');
  assert.strictEqual(T.siteOf('https://X.bandcamp.com/music?x'), 'https://x.bandcamp.com');
});

test('reads release links from an artist page, newest first', () => {
  const html = `<ol id="music-grid" class="editable-grid music-grid">
    <li data-item-id="album-2" class="music-grid-item"><a href="/album/new-one"><p class="title">New</p></a></li>
    <li data-item-id="track-1" class="music-grid-item"><a href="https://other.bandcamp.com/track/old-one?x=1">Old</a></li>
  </ol>`;
  assert.deepStrictEqual(T.releaseLinksFromArtistPage(html, 'https://x.bandcamp.com'),
    ['https://x.bandcamp.com/album/new-one', 'https://other.bandcamp.com/track/old-one']);
  const extra = '<ol id="music-grid" data-client-items="[{&quot;page_url&quot;:&quot;/album/more&quot;}]"></ol>';
  assert.deepStrictEqual(T.releaseLinksFromArtistPage(extra, 'https://x.bandcamp.com'), ['https://x.bandcamp.com/album/more']);
  const single = '<meta property="og:url" content="https://x.bandcamp.com/album/only-one">';
  assert.deepStrictEqual(T.releaseLinksFromArtistPage(single, 'https://x.bandcamp.com'), ['https://x.bandcamp.com/album/only-one']);
});

test('queue: this week\'s top 10 first in rank order, then the region ranking; old picks drop in', () => {
  const items = [
    { releaseUrl: 'e-us', date: '2026-11-24', country: 'United States', locationSource: 'release', source: 'email' },
    { releaseUrl: 't2', top10Week: '2026-11-24', top10Rank: 2, source: 'top10', country: 'Japan', date: '2026-11-24' },
    { releaseUrl: 'e-nl', date: '2026-11-20', country: 'Netherlands', locationSource: 'release', source: 'email' },
    { releaseUrl: 't1', top10Week: '2026-11-24', top10Rank: 1, source: 'top10', country: 'Germany', date: '2026-11-24' },
    { releaseUrl: 'old-be', top10Week: '2026-11-17', top10Rank: 1, source: 'top10', country: 'Belgium', locationSource: 'csv', date: '2026-11-17' }
  ];
  assert.deepStrictEqual(queueOrder(items, 'bene', '2026-11-24').map(i => i.releaseUrl),
    ['t1', 't2', 'e-nl', 'old-be', 'e-us']);
});
