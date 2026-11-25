/**
 * BC Inbox parsing. Pure functions with no Apps Script calls, so they are
 * tested locally with `node --test bc-inbox/test/*.test.js`. In Apps Script
 * every file shares one global scope, so Code.js calls these directly.
 */

/** Lowercase host + path, no query string or fragment; null if not a release link. */
function normalizeReleaseUrl(url) {
  var m = String(url || '').trim().match(/^https?:\/\/([^\/?#\s]+)(\/(album|track)\/[^\/?#\s]+)/i);
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
  var info = { itemType: null, itemId: null, artist: null, title: null, location: null, pageName: null, tags: [] };

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

  // The page owner's name and location ("LUST TAPES", "Amsterdam, Netherlands").
  // On a label's page this is the label, not the artist.
  var block = html.match(/<p id="band-name-location">([\s\S]*?)<\/p>/i);
  var scope = block ? block[1] : html;
  var name = scope.match(/<span class="title">\s*([^<]*?)\s*<\/span>/i);
  if (block && name && name[1]) info.pageName = decodeEntities(name[1]);
  var loc = scope.match(/<span class="location[^"]*">\s*([^<]*?)\s*<\/span>/i);
  if (loc && loc[1]) info.location = decodeEntities(loc[1]);

  var tagRe = /<a class="tag"[^>]*>\s*([^<]+?)\s*<\/a>/gi, t2;
  while ((t2 = tagRe.exec(html)) !== null) {
    var tag = decodeEntities(t2[1]);
    if (info.tags.indexOf(tag) === -1) info.tags.push(tag);
  }
  return info;
}

function embedUrl(info) {
  if (!info.itemId) return null;
  return 'https://bandcamp.com/EmbeddedPlayer/' + info.itemType + '=' + info.itemId +
    '/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/transparent=true/';
}

function sameName(a, b) {
  var norm = function (x) { return String(x || '').toLowerCase().replace(/[^a-z0-9\u00c0-\u024f]+/g, ''); };
  return norm(a) !== '' && norm(a) === norm(b);
}

/**
 * Copy what a release page told us onto a queue item. The location counts as
 * the artist's ("release") when the page belongs to the artist, and as the
 * label's when it belongs to someone else.
 */
function applyEnrichment(item, info) {
  var out = {};
  Object.keys(item).forEach(function (k) { out[k] = item[k]; });
  out.enriched = true;
  if (!info || info.error) { out.enrichError = info ? info.error : 'no data'; return out; }
  out.embedUrl = info.embedUrl || embedUrl(info);
  out.itemId = info.itemId;
  if (info.itemType) out.itemType = info.itemType;
  out.tags = info.tags || [];
  out.pageName = info.pageName || null;
  out.location = info.location || null;
  if (!out.location) out.locationSource = 'unknown';
  else if (info.pageName && !sameName(info.pageName, out.artist)) out.locationSource = 'label';
  else out.locationSource = 'release';
  return out;
}

// --- Release emails -------------------------------------------------------

// Only "New release from …" is a release. "New from X: …", "New item(s) from",
// "New message from", "Thank you!" and "Confirm login" are skipped.
var RELEASE_SUBJECT = /^New release from (.+?)(?:, who brought you .*)?$/;

function isReleaseSubject(subject) {
  return RELEASE_SUBJECT.test(String(subject || '').trim());
}

/**
 * Turn one Bandcamp email into a queue item, or null if it isn't a release.
 * email: { subject, date (ISO string), plain, html }
 */
function parseReleaseEmail(email) {
  var subject = String(email.subject || '').trim();
  var s = subject.match(RELEASE_SUBJECT);
  if (!s) return null;
  var plain = String(email.plain || '').replace(/\r\n/g, '\n');

  // "<Account> just released|announced "<Title>"[ by <Artist>], check it out at:"
  var line = plain.match(/^(.+?) just (released|announced) "(.*)"(?: by (.+?))?, check it out at:\s*$/m);
  if (!line) return null;

  var after = plain.slice(line.index + line[0].length);
  var link = after.match(/https?:\/\/\S+/);
  var releaseUrl = link && normalizeReleaseUrl(link[0]);
  if (!releaseUrl) {
    var any = plain.match(/https?:\/\/[^\s"]+\/(?:album|track)\/[^\s"?#]+/);
    releaseUrl = any && normalizeReleaseUrl(any[0]);
  }
  if (!releaseUrl) return null;

  var followed = line[1].trim() || s[1].trim();
  var via = /you received this because you're following/i.test(plain) ? 'following'
    : /you received this because you bought/i.test(plain) ? 'bought' : null;

  var cover = String(email.html || '').match(/<img[^>]+src="(https:\/\/[^"]*bcbits\.com\/img\/[^"]+)"/i);

  return {
    releaseUrl: releaseUrl,
    itemType: /\/track\//.test(releaseUrl) ? 'track' : 'album',
    artist: line[4] ? line[4].trim() : followed,
    title: line[3],
    followedAccount: followed,
    announced: line[2] === 'announced',
    via: via,
    cover: cover ? decodeEntities(cover[1]) : null,
    date: email.date,
    source: 'email',
    location: null,
    locationSource: 'unknown',
    status: 'queued'
  };
}

/** Merge item lists by releaseUrl. The first one seen for a release wins. Newest first. */
function mergeItems(lists) {
  var seen = {};
  var out = [];
  for (var i = 0; i < lists.length; i++) {
    var list = lists[i] || [];
    for (var j = 0; j < list.length; j++) {
      var item = list[j];
      if (!item || seen[item.releaseUrl]) continue;
      seen[item.releaseUrl] = true;
      out.push(item);
    }
  }
  out.sort(function (a, b) { return String(b.date).localeCompare(String(a.date)); });
  return out;
}

/**
 * Pull the text/plain and text/html bodies out of a Gmail API message payload.
 * decode turns a base64url string into text (Apps Script passes one built on
 * Utilities; the tests pass Buffer).
 */
function bodiesFromPayload(payload, decode) {
  var out = { plain: '', html: '' };
  (function walk(part) {
    if (!part) return;
    var type = (part.mimeType || '').toLowerCase();
    var data = part.body && part.body.data;
    if (data && type === 'text/plain' && !out.plain) out.plain = decode(data);
    if (data && type === 'text/html' && !out.html) out.html = decode(data);
    (part.parts || []).forEach(walk);
  })(payload);
  return out;
}

/** Add the '=' padding base64 decoders want; Gmail's base64url omits it. */
function padBase64(s) {
  s = String(s).replace(/\s+/g, '');
  return s + '===='.slice(0, (4 - s.length % 4) % 4);
}

function headerValue(payload, name) {
  var headers = (payload && payload.headers) || [];
  for (var i = 0; i < headers.length; i++) {
    if (String(headers[i].name).toLowerCase() === name.toLowerCase()) return headers[i].value;
  }
  return '';
}

if (typeof module !== 'undefined') {
  module.exports = {
    normalizeReleaseUrl: normalizeReleaseUrl, parseReleasePage: parseReleasePage, embedUrl: embedUrl,
    isReleaseSubject: isReleaseSubject, parseReleaseEmail: parseReleaseEmail, mergeItems: mergeItems,
    bodiesFromPayload: bodiesFromPayload, headerValue: headerValue, padBase64: padBase64,
    applyEnrichment: applyEnrichment, sameName: sameName
  };
}
