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
