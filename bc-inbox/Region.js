/**
 * BC Inbox regions: turn a Bandcamp location string into a country, and rank
 * the queue by the selected region. Pure functions, tested with node.
 */

var REGIONS = {
  bene: { label: 'BeNe', countries: ['Netherlands', 'Belgium'] },
  nl: { label: 'Netherlands', countries: ['Netherlands'] },
  be: { label: 'Belgium', countries: ['Belgium'] },
  de: { label: 'Germany', countries: ['Germany'] },
  ukie: { label: 'UK & Ireland', countries: ['United Kingdom', 'Ireland'] },
  fr: { label: 'France', countries: ['France'] },
  nordics: { label: 'Nordics', countries: ['Denmark', 'Norway', 'Sweden', 'Finland', 'Iceland'] },
  europe: { label: 'Europe', countries: [
    'Netherlands', 'Belgium', 'Luxembourg', 'Germany', 'France', 'United Kingdom', 'Ireland',
    'Denmark', 'Norway', 'Sweden', 'Finland', 'Iceland', 'Spain', 'Portugal', 'Italy',
    'Switzerland', 'Austria', 'Poland', 'Czech Republic', 'Slovakia', 'Hungary', 'Slovenia',
    'Croatia', 'Serbia', 'Bosnia and Herzegovina', 'Montenegro', 'North Macedonia', 'Albania',
    'Greece', 'Bulgaria', 'Romania', 'Moldova', 'Ukraine', 'Belarus', 'Lithuania', 'Latvia',
    'Estonia', 'Malta', 'Cyprus', 'Monaco', 'Andorra', 'Liechtenstein', 'San Marino']
  },
  na: { label: 'North America', countries: ['United States', 'Canada', 'Mexico'] },
  anywhere: { label: 'Anywhere (no ranking)', countries: null }
};
var DEFAULT_REGION = 'bene';

var COUNTRY_ALIASES = {
  'the netherlands': 'Netherlands', 'nederland': 'Netherlands', 'holland': 'Netherlands', 'nl': 'Netherlands',
  'belgië': 'Belgium', 'belgie': 'Belgium', 'belgique': 'Belgium', 'belgien': 'Belgium',
  'deutschland': 'Germany',
  'uk': 'United Kingdom', 'u.k.': 'United Kingdom', 'england': 'United Kingdom', 'scotland': 'United Kingdom',
  'wales': 'United Kingdom', 'northern ireland': 'United Kingdom', 'great britain': 'United Kingdom', 'britain': 'United Kingdom',
  'usa': 'United States', 'us': 'United States', 'u.s.': 'United States', 'u.s.a.': 'United States',
  'united states of america': 'United States', 'america': 'United States',
  'czechia': 'Czech Republic'
};

// Bandcamp often writes US and Canadian places as "City, State".
var STATE_COUNTRY = {};
['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
  'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
  'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
  'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
  'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
  'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
  'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia', 'Washington, D.C.'
].forEach(function (s) { STATE_COUNTRY[s.toLowerCase()] = 'United States'; });
['Ontario', 'Quebec', 'Québec', 'British Columbia', 'Alberta', 'Manitoba', 'Saskatchewan',
  'Nova Scotia', 'New Brunswick', 'Newfoundland and Labrador', 'Prince Edward Island'
].forEach(function (s) { STATE_COUNTRY[s.toLowerCase()] = 'Canada'; });
// "Georgia" is a US state far more often than the country on Bandcamp.

// Places Bandcamp sometimes gives without a country.
var CITY_COUNTRY = {
  'amsterdam': 'Netherlands', 'rotterdam': 'Netherlands', 'utrecht': 'Netherlands', 'the hague': 'Netherlands',
  'den haag': 'Netherlands', "'s-gravenhage": 'Netherlands', 'eindhoven': 'Netherlands', 'groningen': 'Netherlands',
  'nijmegen': 'Netherlands', 'tilburg': 'Netherlands', 'arnhem': 'Netherlands', 'haarlem': 'Netherlands',
  'leiden': 'Netherlands', 'breda': 'Netherlands', 'zwolle': 'Netherlands', 'maastricht': 'Netherlands',
  'enschede': 'Netherlands', 'den bosch': 'Netherlands', "'s-hertogenbosch": 'Netherlands', 'delft': 'Netherlands',
  'brussels': 'Belgium', 'bruxelles': 'Belgium', 'brussel': 'Belgium', 'antwerp': 'Belgium', 'antwerpen': 'Belgium',
  'ghent': 'Belgium', 'gent': 'Belgium', 'liège': 'Belgium', 'liege': 'Belgium', 'leuven': 'Belgium',
  'bruges': 'Belgium', 'brugge': 'Belgium', 'mechelen': 'Belgium', 'kortrijk': 'Belgium', 'hasselt': 'Belgium',
  'berlin': 'Germany', 'hamburg': 'Germany', 'cologne': 'Germany', 'köln': 'Germany', 'munich': 'Germany',
  'leipzig': 'Germany', 'london': 'United Kingdom', 'manchester': 'United Kingdom', 'glasgow': 'United Kingdom',
  'bristol': 'United Kingdom', 'dublin': 'Ireland', 'paris': 'France', 'lyon': 'France',
  'brooklyn': 'United States', 'new york city': 'United States', 'los angeles': 'United States', 'chicago': 'United States'
};

var KNOWN_COUNTRIES = {};
Object.keys(REGIONS).forEach(function (k) {
  (REGIONS[k].countries || []).forEach(function (c) { KNOWN_COUNTRIES[c.toLowerCase()] = c; });
});
['Japan', 'Australia', 'New Zealand', 'Brazil', 'Argentina', 'Chile', 'Colombia', 'Peru', 'China',
  'South Korea', 'Taiwan', 'Indonesia', 'Philippines', 'Singapore', 'Malaysia', 'Thailand', 'India',
  'Israel', 'Turkey', 'Russia', 'South Africa', 'Egypt', 'Morocco', 'Tunisia', 'Lebanon', 'Iran'
].forEach(function (c) { KNOWN_COUNTRIES[c.toLowerCase()] = c; });

/** "Rotterdam, Netherlands" → "Netherlands"; "Brooklyn, New York" → "United States"; null if unknown. */
function countryOf(location) {
  if (!location) return null;
  var parts = String(location).split(',').map(function (p) { return p.trim(); }).filter(Boolean);
  for (var i = parts.length - 1; i >= 0; i--) {
    var p = parts[i].toLowerCase();
    if (COUNTRY_ALIASES[p]) return COUNTRY_ALIASES[p];
    if (KNOWN_COUNTRIES[p]) return KNOWN_COUNTRIES[p];
    if (STATE_COUNTRY[p]) return STATE_COUNTRY[p];
    if (CITY_COUNTRY[p]) return CITY_COUNTRY[p];
  }
  return null;
}

/**
 * Rank for one item in a region: 0 the artist's own location matches, 1 only
 * the label's location matches, 2 everything else (unknown location too).
 */
function regionRank(item, regionKey) {
  var region = REGIONS[regionKey] || REGIONS[DEFAULT_REGION];
  if (!region.countries) return 0;
  var country = item.country || countryOf(item.location);
  if (!country || region.countries.indexOf(country) === -1) return 2;
  return item.locationSource === 'label' ? 1 : 0;
}

/** Order the queue for a region: rank first, then newest first. Nothing is dropped. */
function rankItems(items, regionKey) {
  return items.slice().sort(function (a, b) {
    var r = regionRank(a, regionKey) - regionRank(b, regionKey);
    if (r) return r;
    return String(b.date).localeCompare(String(a.date));
  });
}

if (typeof module !== 'undefined') {
  module.exports = { REGIONS: REGIONS, DEFAULT_REGION: DEFAULT_REGION, countryOf: countryOf, regionRank: regionRank, rankItems: rankItems };
}
