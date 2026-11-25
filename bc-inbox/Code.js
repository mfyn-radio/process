/**
 * BC Inbox server. Parsing lives in Parse.js (pure, tested with node).
 * Gmail is read through the Gmail API advanced service with the
 * gmail.readonly scope only: the script cannot send, label, archive or
 * delete email.
 */

var GMAIL_QUERY = 'from:noreply@bandcamp.com subject:"New release from"';
var FIRST_LOAD_DAYS = 30;
var MAX_MESSAGES = 300;

// The release the page plays unless ?url= names another one (milestone 1 check).
var DEFAULT_RELEASE = 'https://lusttapes.bandcamp.com/album/sociopathic-morbid-aberrations';

function doGet(e) {
  var page = HtmlService.createTemplateFromFile('index');
  page.startUrl = (e && e.parameter && e.parameter.url) || '';
  // The page ranks with the same code as the tests: Region.js's functions,
  // sent as source. Countries are worked out on the server.
  page.regionScript = ('var REGIONS = ' + JSON.stringify(REGIONS) + ';\n' +
    'var DEFAULT_REGION = ' + JSON.stringify(DEFAULT_REGION) + ';\n' +
    'function countryOf() { return null; }\n' +
    regionRank.toString() + '\n' + rankItems.toString() + '\n' + queueOrder.toString()).replace(/<\//g, '<\\/');
  return page.evaluate()
    .setTitle('BC Inbox')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * Called from the page: release emails newer than sinceMs (epoch ms), or the
 * last FIRST_LOAD_DAYS days when sinceMs is empty. Returns { items, syncedAt }.
 */
function getReleaseEmails(sinceMs) {
  var now = Date.now();
  var since = sinceMs ? Number(sinceMs) : now - FIRST_LOAD_DAYS * 24 * 3600 * 1000;
  // Gmail's after: takes epoch seconds. Step back an hour for clock skew;
  // the page dedupes by release URL anyway.
  var query = GMAIL_QUERY + ' after:' + Math.floor((since - 3600 * 1000) / 1000);

  var ids = [];
  var pageToken;
  do {
    var res = Gmail.Users.Messages.list('me', { q: query, maxResults: 100, pageToken: pageToken });
    (res.messages || []).forEach(function (m) { ids.push(m.id); });
    pageToken = res.nextPageToken;
  } while (pageToken && ids.length < MAX_MESSAGES);

  var items = [];
  var failed = 0;
  ids.slice(0, MAX_MESSAGES).forEach(function (id) {
    try {
      var msg = Gmail.Users.Messages.get('me', id, { format: 'full' });
      var bodies = bodiesFromPayload(msg.payload, decodeBody);
      var item = parseReleaseEmail({
        subject: headerValue(msg.payload, 'Subject'),
        date: new Date(Number(msg.internalDate)).toISOString(),
        plain: bodies.plain,
        html: bodies.html
      });
      if (item) {
        item.messageId = id;
        items.push(item);
      }
    } catch (err) {
      // One odd email must not break the whole list.
      failed++;
      console.warn('BC Inbox: could not read message ' + id + ': ' + err);
    }
  });
  return { items: mergeItems([items]), syncedAt: now, scanned: ids.length, failed: failed };
}

/**
 * A Gmail API body. The advanced service usually hands it over already
 * decoded to bytes; if it comes as a base64url string, Gmail leaves off the
 * '=' padding that Utilities.base64DecodeWebSafe needs.
 */
function decodeBody(data) {
  if (Array.isArray(data)) return Utilities.newBlob(data).getDataAsString('UTF-8');
  return Utilities.newBlob(Utilities.base64DecodeWebSafe(padBase64(String(data)))).getDataAsString('UTF-8');
}

// Release pages are fetched at most once per release: CacheService for 6 hours,
// script properties for good. Fetches are paced, and one call stops after
// ENRICH_BUDGET_MS so the page can show progress and ask for the rest.
var ENRICH_BUDGET_MS = 20000;
var FETCH_PAUSE_MS = 400;
var CACHE_PREFIX = 'rel1:';

/** Called from the page: release-page facts for each URL, from cache or fetched. Returns { results, remaining }. */
function enrichReleases(urls) {
  var started = Date.now();
  var cache = CacheService.getScriptCache();
  var props = PropertiesService.getScriptProperties();
  var results = {};
  var remaining = [];
  var fetched = 0;
  (urls || []).forEach(function (raw) {
    var url = normalizeReleaseUrl(raw);
    if (!url) { results[raw] = { error: 'not a release link' }; return; }
    var key = CACHE_PREFIX + url;
    var hit = cache.get(key) || props.getProperty(key);
    if (hit) { results[raw] = JSON.parse(hit); return; }
    if (Date.now() - started > ENRICH_BUDGET_MS) { remaining.push(raw); return; }
    if (fetched > 0) Utilities.sleep(FETCH_PAUSE_MS);
    fetched++;
    var info = fetchReleaseInfo(url);
    var json = JSON.stringify(info);
    cache.put(key, json, 21600);
    // A temporary failure (5xx, network) is cached briefly but not kept for good.
    if (!info.error || info.permanent) {
      try { props.setProperty(key, json); } catch (err) { console.warn('BC Inbox: property store full? ' + err); }
    }
    results[raw] = info;
  });
  return { results: results, remaining: remaining, fetched: fetched };
}

function fetchReleaseInfo(url) {
  try {
    var response = UrlFetchApp.fetch(url, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: { 'User-Agent': 'Mozilla/5.0 (BC Inbox for MFYN)' }
    });
    var status = response.getResponseCode();
    if (status !== 200) return { error: 'HTTP ' + status, permanent: status === 404 || status === 410 };
    var info = parseReleasePage(response.getContentText());
    info.embedUrl = embedUrl(info);
    info.fetchedAt = new Date().toISOString();
    return info;
  } catch (err) {
    return { error: String(err), permanent: false };
  }
}

/**
 * Called from the page with queue items that have no location yet. Returns
 * the items with location, country, label/artist source, player and tags
 * filled in, plus how many are left for the next call.
 */
function enrichItems(items) {
  var res = enrichReleases((items || []).map(function (it) { return it.releaseUrl; }));
  var out = [];
  (items || []).forEach(function (it) {
    var info = res.results[it.releaseUrl];
    if (!info) return; // left for the next call
    var enriched = applyEnrichment(it, info);
    enriched.country = countryOf(enriched.location);
    out.push(enriched);
  });
  return { items: out, remaining: res.remaining.length, fetched: res.fetched };
}

// --- Weekly top 10 -------------------------------------------------------

// The rising-artists run saves rising-artists-YYYY-MM-DD.csv here, in mfyn@'s Drive.
var TOP10_FOLDER = 'MFYN_Rising_Artists';
var RESOLVE_PREFIX = 'art1:';

/** Called from the page: this week's top 10 from the newest CSV in TOP10_FOLDER. */
function getTopTen() {
  var files = [];
  var folders = DriveApp.getFoldersByName(TOP10_FOLDER);
  if (!folders.hasNext()) return { missing: 'folder', folder: TOP10_FOLDER, items: [] };
  while (folders.hasNext()) {
    var it = folders.next().getFiles();
    while (it.hasNext()) {
      var f = it.next();
      files.push({ name: f.getName(), id: f.getId() });
    }
  }
  var newest = newestTop10File(files);
  if (!newest) return { missing: 'file', folder: TOP10_FOLDER, items: [] };
  var text = DriveApp.getFileById(newest.id).getBlob().getDataAsString('UTF-8');
  return { fileName: newest.name, week: newest.week, items: resolveTop10(top10Items(text, newest.week)) };
}

/** Called from the page with a CSV picked by hand (the fallback). */
function topTenFromCsv(text, fileName) {
  var week = weekOfFile(fileName) || Utilities.formatDate(new Date(), 'Europe/Amsterdam', 'yyyy-MM-dd');
  return { fileName: fileName, week: week, items: resolveTop10(top10Items(text, week)) };
}

/**
 * Give each pick a playable release: its own link if it is one, else the
 * suggested track on the artist's site, else the newest release there. Then
 * fill in the player and tags like an email item, keeping the CSV's location.
 */
function resolveTop10(items) {
  var props = PropertiesService.getScriptProperties();
  items.forEach(function (it) {
    if (it.releaseUrl || it.linkKind !== 'artist') return;
    var site = siteOf(it.sourceUrl);
    var key = RESOLVE_PREFIX + site + '|' + (it.suggestedTrack || '');
    var cached = props.getProperty(key);
    if (cached) { it.releaseUrl = cached === '-' ? null : cached; return; }
    var found = null;
    if (it.suggestedTrack) {
      var guess = normalizeReleaseUrl(site + '/track/' + slugify(it.suggestedTrack));
      var info = guess && enrichReleases([guess]).results[guess];
      if (info && !info.error && info.itemId) found = guess;
    }
    if (!found) {
      var page = fetchPage(site + '/music');
      if (page) found = releaseLinksFromArtistPage(page, site)[0] || null;
    }
    it.releaseUrl = found;
    props.setProperty(key, found || '-');
  });

  var urls = items.map(function (it) { return it.releaseUrl; }).filter(Boolean);
  var results = {};
  var guard = 0;
  while (urls.length && guard++ < 10) {
    var res = enrichReleases(urls);
    Object.keys(res.results).forEach(function (u) { results[u] = res.results[u]; });
    urls = res.remaining;
  }
  return items.map(function (it) {
    var out;
    if (!it.releaseUrl) {
      out = applyEnrichment(it, { error: it.sourceUrl ? 'no release found at ' + it.sourceUrl : 'no Bandcamp link in the CSV' });
    } else {
      var info = results[it.releaseUrl];
      out = applyEnrichment(it, info);
      if (info && !info.error && info.title) {
        out.releaseTitle = info.title;
        out.title = info.title;
      }
    }
    if (it.location) { out.location = it.location; out.locationSource = 'csv'; }
    if (it.tags && it.tags.length) out.tags = it.tags;
    out.country = countryOf(out.location);
    out.key = out.releaseUrl || ('top10:' + it.top10Week + ':' + it.top10Rank);
    return out;
  });
}

function fetchPage(url) {
  try {
    var r = UrlFetchApp.fetch(url, {
      muteHttpExceptions: true, followRedirects: true,
      headers: { 'User-Agent': 'Mozilla/5.0 (BC Inbox for MFYN)' }
    });
    return r.getResponseCode() === 200 ? r.getContentText() : null;
  } catch (err) {
    return null;
  }
}

/** Called from the page: one release's player info (used by ?url=). */
function loadRelease(url) {
  var clean = normalizeReleaseUrl(url);
  if (!clean) throw new Error('Not a Bandcamp album or track link: ' + url);
  var info = enrichReleases([clean]).results[clean];
  if (info.error) throw new Error('Bandcamp: ' + info.error + ' for ' + clean);
  info.releaseUrl = clean;
  return info;
}
