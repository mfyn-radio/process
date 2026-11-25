/**
 * BC Inbox top 10: the weekly rising-artists CSV. Pure functions, tested with
 * node. Columns: Artist, Location, Bandcamp URL, Suggested track, Tags,
 * IG handle, IG followers, Fit notes, Rising notes, Next BeNe show, Contact.
 * Row order is the run's ranking.
 */

var TOP10_FILE = /^rising-artists-(\d{4}-\d{2}-\d{2})\.csv$/i;

/** RFC 4180-ish CSV: quoted fields, doubled quotes, commas and newlines inside quotes. */
function parseCsv(text) {
  var rows = [], row = [], field = '', i = 0, q = false;
  text = String(text || '').replace(/^﻿/, '');
  while (i < text.length) {
    var c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 2; continue; }
      if (c === '"') { q = false; i++; continue; }
      field += c; i++; continue;
    }
    if (c === '"') { q = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\r') { i++; continue; }
    if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
    field += c; i++;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter(function (r) { return r.some(function (f) { return f.trim() !== ''; }); });
}

/** CSV text → objects keyed by trimmed header names. */
function csvRecords(text) {
  var rows = parseCsv(text);
  if (!rows.length) return [];
  var head = rows[0].map(function (h) { return h.trim(); });
  return rows.slice(1).map(function (r) {
    var o = {};
    head.forEach(function (h, j) { o[h] = (r[j] || '').trim(); });
    return o;
  });
}

/** "rising-artists-2026-11-24.csv" → "2026-11-24", else null. */
function weekOfFile(name) {
  var m = String(name || '').match(TOP10_FILE);
  return m ? m[1] : null;
}

/** The newest file by the date in its name; files without one are ignored. */
function newestTop10File(files) {
  var best = null;
  (files || []).forEach(function (f) {
    var w = weekOfFile(f.name);
    if (w && (!best || w > best.week)) best = { name: f.name, id: f.id, week: w };
  });
  return best;
}

/**
 * What kind of Bandcamp link: 'release' (album/track page), 'artist' (an
 * artist or label home or /music page), or null.
 */
function linkKind(url) {
  var m = String(url || '').trim().match(/^https?:\/\/([^\/?#\s]+)(\/[^?#\s]*)?/i);
  if (!m) return null;
  var path = (m[2] || '/').toLowerCase();
  if (/^\/(album|track)\/[^\/]+/.test(path)) return 'release';
  if (path === '/' || path === '' || /^\/music\/?$/.test(path)) return 'artist';
  return null;
}

function slugify(s) {
  return String(s || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

/** https://x.bandcamp.com/whatever → https://x.bandcamp.com */
function siteOf(url) {
  var m = String(url || '').match(/^(https?:\/\/[^\/?#\s]+)/i);
  return m ? m[1].replace(/^http:/i, 'https:').toLowerCase() : null;
}

/**
 * Release links on an artist's page, in page order (Bandcamp shows the
 * artist's own order, usually newest first). Also reads og:url, for artist
 * pages that show a single release directly.
 */
function releaseLinksFromArtistPage(html, site) {
  var out = [];
  var add = function (href) {
    var abs = /^https?:/i.test(href) ? href : site + (href.charAt(0) === '/' ? '' : '/') + href;
    var u = normalizeReleaseUrl(decodeEntities(abs));
    if (u && out.indexOf(u) === -1) out.push(u);
  };
  var grid = html.match(/<ol[^>]*id="music-grid"[\s\S]*?<\/ol>/i);
  var scope = grid ? grid[0] : html;
  var re = /href="([^"]*\/(?:album|track)\/[^"?#]+)[^"]*"/gi, m;
  while ((m = re.exec(scope)) !== null) add(m[1]);
  var items = html.match(/data-client-items="([^"]*)"/i);
  if (items) {
    try {
      JSON.parse(decodeEntities(items[1])).forEach(function (it) { if (it.page_url) add(it.page_url); });
    } catch (e) { /* ignore */ }
  }
  if (!out.length) {
    var og = html.match(/<meta\s+property="og:url"\s+content="([^"]*)"/i);
    if (og) add(og[1]);
  }
  return out;
}

/** Turn one CSV record into a top-10 item (releaseUrl may still need resolving). */
function top10Item(rec, rank, week) {
  var url = rec['Bandcamp URL'] || '';
  var kind = linkKind(url);
  var location = rec['Location'] || null;
  return {
    releaseUrl: kind === 'release' ? normalizeReleaseUrl(url) : null,
    sourceUrl: url || null,
    linkKind: kind,
    artist: rec['Artist'] || '?',
    title: rec['Suggested track'] || '',
    suggestedTrack: rec['Suggested track'] || null,
    location: location,
    locationSource: location ? 'csv' : 'unknown',
    tags: (rec['Tags'] || '').split(/[,;]/).map(function (t) { return t.trim(); }).filter(Boolean),
    igHandle: rec['IG handle'] || null,
    igFollowers: rec['IG followers'] || null,
    fitNotes: rec['Fit notes'] || null,
    risingNotes: rec['Rising notes'] || null,
    nextBeneShow: rec['Next BeNe show'] || null,
    contact: rec['Contact'] || null,
    source: 'top10',
    top10Week: week,
    top10Rank: rank,
    date: week,
    status: 'queued'
  };
}

/** All the records of a CSV as top-10 items, in ranked order. */
function top10Items(csvText, week) {
  return csvRecords(csvText)
    .filter(function (r) { return r['Artist'] || r['Bandcamp URL']; })
    .map(function (r, i) { return top10Item(r, i + 1, week); });
}

if (typeof module !== 'undefined') {
  // Uses normalizeReleaseUrl and decodeEntities from Parse.js: in Apps Script
  // all files share globals; the node tests put them on the global object.
  module.exports = {
    parseCsv: parseCsv, csvRecords: csvRecords, weekOfFile: weekOfFile, newestTop10File: newestTop10File,
    linkKind: linkKind, slugify: slugify, siteOf: siteOf, releaseLinksFromArtistPage: releaseLinksFromArtistPage,
    top10Item: top10Item, top10Items: top10Items
  };
}
