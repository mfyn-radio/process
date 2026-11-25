/**
 * BC Inbox, milestone 1 (spike): can an Apps Script web app play a Bandcamp
 * release on a phone? The page fetches one release server-side, reads its
 * embed ID and location, and shows Bandcamp's embedded player.
 *
 * The parsing functions below use no Apps Script services, so they are
 * tested locally with `node --test bc-inbox/test`.
 */

// The release the spike plays unless ?url= names another one.
var DEFAULT_RELEASE = 'https://lusttapes.bandcamp.com/album/sociopathic-morbid-aberrations';

function doGet(e) {
  var page = HtmlService.createTemplateFromFile('index');
  page.startUrl = (e && e.parameter && e.parameter.url) || DEFAULT_RELEASE;
  return page.evaluate()
    .setTitle('BC Inbox')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/** Called from the page: fetch a release page and return what the player needs. */
function loadRelease(url) {
  var clean = normalizeReleaseUrl(url);
  if (!clean) throw new Error('Not a Bandcamp album or track link: ' + url);
  var response = UrlFetchApp.fetch(clean, {
    muteHttpExceptions: true,
    followRedirects: true,
    headers: { 'User-Agent': 'Mozilla/5.0 (BC Inbox for MFYN)' }
  });
  var status = response.getResponseCode();
  if (status !== 200) throw new Error('Bandcamp answered HTTP ' + status + ' for ' + clean);
  var info = parseReleasePage(response.getContentText());
  info.releaseUrl = clean;
  info.embedUrl = embedUrl(info);
  return info;
}

/** Lowercase host + path, no query string or fragment; null if not a release link. */
function normalizeReleaseUrl(url) {
  var m = String(url || '').trim().match(/^https?:\/\/([^\/?#]+\.bandcamp\.com|[^\/?#]+)(\/(album|track)\/[^\/?#]+)/i);
  if (!m) return null;
  return 'https://' + m[1].toLowerCase() + m[2].toLowerCase();
}

function decodeEntities(s) {
  return String(s)
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

/** Read the embed ID, type, artist, title and location from a release page's HTML. */
function parseReleasePage(html) {
  var info = { itemType: null, itemId: null, artist: null, title: null, location: null };

  var props = html.match(/<meta\s+name="bc-page-properties"\s+content="([^"]*)"/i);
  if (props) {
    try {
      var p = JSON.parse(decodeEntities(props[1]));
      if (p.item_id) {
        info.itemId = String(p.item_id);
        info.itemType = p.item_type === 't' ? 'track' : 'album';
      }
    } catch (err) { /* fall through to og:video */ }
  }
  if (!info.itemId) {
    var video = html.match(/EmbeddedPlayer\/(?:v=2\/)?(album|track)=(\d+)/i);
    if (video) { info.itemType = video[1].toLowerCase(); info.itemId = video[2]; }
  }

  var title = html.match(/<meta\s+property="og:title"\s+content="([^"]*)"/i);
  if (title) {
    // "Release, by Artist"
    var t = decodeEntities(title[1]);
    var split = t.lastIndexOf(', by ');
    if (split > -1) { info.title = t.slice(0, split); info.artist = t.slice(split + 5); }
    else info.title = t;
  }

  var loc = html.match(/<span class="location[^"]*">\s*([^<]*?)\s*<\/span>/i);
  if (loc && loc[1]) info.location = decodeEntities(loc[1]);
  return info;
}

function embedUrl(info) {
  if (!info.itemId) return null;
  return 'https://bandcamp.com/EmbeddedPlayer/' + info.itemType + '=' + info.itemId +
    '/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/transparent=true/';
}

if (typeof module !== 'undefined') {
  module.exports = { normalizeReleaseUrl: normalizeReleaseUrl, parseReleasePage: parseReleasePage, embedUrl: embedUrl };
}
