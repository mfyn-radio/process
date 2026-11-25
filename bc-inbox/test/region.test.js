const test = require('node:test');
const assert = require('node:assert');
const { countryOf, regionRank, rankItems, REGIONS, sectionNames } = require('../Region.js');

test('countryOf reads Bandcamp location strings', () => {
  assert.strictEqual(countryOf('Rotterdam, Netherlands'), 'Netherlands');
  assert.strictEqual(countryOf('Amsterdam, Netherlands'), 'Netherlands');
  assert.strictEqual(countryOf('Ghent, Belgium'), 'Belgium');
  assert.strictEqual(countryOf('Brooklyn, New York'), 'United States');
  assert.strictEqual(countryOf('Lancaster, Pennsylvania'), 'United States');
  assert.strictEqual(countryOf('Montréal, Québec'), 'Canada');
  assert.strictEqual(countryOf('London, UK'), 'United Kingdom');
  assert.strictEqual(countryOf('Glasgow, Scotland'), 'United Kingdom');
  assert.strictEqual(countryOf('Antwerpen'), 'Belgium');
  assert.strictEqual(countryOf('Tokyo, Japan'), 'Japan');
  assert.strictEqual(countryOf('Somewhere Unknown'), null);
  assert.strictEqual(countryOf(null), null);
});

test('every region preset from the plan exists', () => {
  assert.deepStrictEqual(Object.keys(REGIONS),
    ['bene', 'nl', 'be', 'de', 'ukie', 'fr', 'nordics', 'europe', 'na', 'anywhere']);
});

const items = [
  { releaseUrl: 'us-new', date: '2026-11-24', location: 'Brooklyn, New York', locationSource: 'release' },
  { releaseUrl: 'nl-label', date: '2026-11-23', location: 'Amsterdam, Netherlands', locationSource: 'label' },
  { releaseUrl: 'be-old', date: '2026-11-01', location: 'Ghent, Belgium', locationSource: 'release' },
  { releaseUrl: 'unknown', date: '2026-11-25', location: null, locationSource: 'unknown' },
  { releaseUrl: 'nl-new', date: '2026-11-20', country: 'Netherlands', locationSource: 'release' }
];

test('BeNe: artist matches, then label-only matches, then the rest, each newest first', () => {
  assert.deepStrictEqual(rankItems(items, 'bene').map(i => i.releaseUrl),
    ['nl-new', 'be-old', 'nl-label', 'unknown', 'us-new']);
  assert.strictEqual(regionRank(items[3], 'bene'), 2);
});

test('changing region reorders without dropping anything', () => {
  const na = rankItems(items, 'na').map(i => i.releaseUrl);
  assert.strictEqual(na[0], 'us-new');
  assert.strictEqual(na.length, items.length);
  assert.deepStrictEqual(rankItems(items, 'anywhere').map(i => i.releaseUrl),
    ['unknown', 'us-new', 'nl-label', 'nl-new', 'be-old']);
});

test('section names follow the region', () => {
  assert.deepStrictEqual(sectionNames('bene'), { artists: 'BeNe artists', labels: 'BeNe labels' });
  assert.deepStrictEqual(sectionNames('nl'), { artists: 'Dutch artists', labels: 'Dutch labels' });
  assert.deepStrictEqual(sectionNames('fr'), { artists: 'French artists', labels: 'French labels' });
});
