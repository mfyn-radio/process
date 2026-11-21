// Dot-matrix text. Glyphs come from the PixelFonts collection
// (github.com/mcer12/PixelFonts), converted to data/fonts.json because
// Processing can't read the original BDF files.

HashMap<String, PixelFont> FONTS = new HashMap<String, PixelFont>();

class PixelFont {
  int height;
  HashMap<Character, int[][]> rows = new HashMap<Character, int[][]>();
  HashMap<Character, Integer> adv = new HashMap<Character, Integer>();
}

void loadFonts() {
  JSONObject all = loadJSONObject("fonts.json");
  for (Object k : all.keys()) {
    String key = (String) k;
    JSONObject fj = all.getJSONObject(key);
    PixelFont pf = new PixelFont();
    pf.height = fj.getInt("height");
    JSONObject gl = fj.getJSONObject("glyphs");
    for (Object ck : gl.keys()) {
      String cs = (String) ck;
      JSONObject g = gl.getJSONObject(cs);
      JSONArray rs = g.getJSONArray("rows");
      int[][] bits = new int[rs.size()][];
      for (int j = 0; j < rs.size(); j++) {
        String row = rs.getString(j);
        bits[j] = new int[row.length()];
        for (int i = 0; i < row.length(); i++) bits[j][i] = row.charAt(i) == '1' ? 1 : 0;
      }
      pf.rows.put(cs.charAt(0), bits);
      pf.adv.put(cs.charAt(0), g.getInt("adv"));
    }
    // Ø: the font's own O with its slash through it
    if (pf.rows.containsKey('O') && pf.rows.containsKey('/')) {
      int[][] o = pf.rows.get('O'), sl = pf.rows.get('/');
      int[][] g = new int[o.length][];
      int holes = 0;
      for (int j = 0; j < o.length; j++) {
        g[j] = o[j].clone();
        for (int i = 0; i < g[j].length && j < sl.length && i < sl[j].length; i++) g[j][i] |= sl[j][i];
        for (int i = 0; i < g[j].length; i++) holes += 1 - g[j][i];
      }
      int adv = pf.adv.get('O');
      // narrow fonts: the slash would fill the O, so widen the O by two
      // pixels and draw a one-pixel diagonal across the wider inside
      if (holes < 4) {
        int w = o[0].length, h = o.length, nw = w + 2;
        int r0 = -1, r1 = -1;
        g = new int[h][nw];
        for (int j = 0; j < h; j++) {
          for (int i = 0; i < nw; i++) g[j][i] = i < 2 ? o[j][i] : i >= nw - 2 ? o[j][w - (nw - i)] : o[j][w / 2];
          if (o[j][w / 2] == 0) { if (r0 < 0) r0 = j; r1 = j; }
        }
        for (int j = r0; r0 >= 0 && j <= r1; j++) g[j][2 + round((r1 - j) * (nw - 5) / float(max(1, r1 - r0)))] = 1;
        adv += 2;
      }
      pf.rows.put('Ø', g);
      pf.adv.put('Ø', adv);
    }
    FONTS.put(key, pf);
  }
}

// Letters the fonts don't have: Æ -> AE, accents dropped (Å -> A, É -> E). Ø is built above.
String fold(String s, PixelFont pf) {
  StringBuilder b = new StringBuilder();
  for (int i = 0; i < s.length(); i++) {
    char c = s.charAt(i);
    if (pf.rows.containsKey(c)) { b.append(c); continue; }
    if (c == 'Æ' || c == 'æ') { b.append("AE"); continue; }
    if (c == 'Œ' || c == 'œ') { b.append("OE"); continue; }
    if (c == 'ß') { b.append("SS"); continue; }
    if (c == 'ø') { b.append(pf.rows.containsKey('Ø') ? 'Ø' : 'O'); continue; }
    String d = java.text.Normalizer.normalize(String.valueOf(c), java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "");
    b.append(d.length() > 0 ? d : "?");
  }
  return b.toString();
}

// render a string to a 0/1 bitmap (rows x cols), trailing empty columns trimmed
float[][] bitmap(String s, String font) {
  PixelFont pf = FONTS.get(font);
  s = fold(s, pf);
  int total = 0;
  for (int i = 0; i < s.length(); i++) total += advance(pf, s.charAt(i));
  float[][] bm = new float[pf.height][total + 64];
  int x = 0, last = -1;
  for (int i = 0; i < s.length(); i++) {
    char c = s.charAt(i);
    int[][] g = pf.rows.containsKey(c) ? pf.rows.get(c) : pf.rows.get('?');
    for (int j = 0; j < g.length; j++) for (int k = 0; k < g[j].length; k++) {
      if (g[j][k] == 1) { bm[j][x + k] = 1; last = max(last, x + k); }
    }
    x += advance(pf, c);
  }
  int cols = max(last + 1, 1);
  float[][] out = new float[pf.height][cols];
  for (int j = 0; j < pf.height; j++) System.arraycopy(bm[j], 0, out[j], 0, cols);
  return out;
}

int advance(PixelFont pf, char c) {
  return pf.adv.containsKey(c) ? pf.adv.get(c) : pf.adv.get('?');
}

int cols(float[][] bm) { return bm.length > 0 ? bm[0].length : 0; }

// draw a bitmap as lit dots with pitch p, plus a soft glow
int dm(Canvas cv, float x0, float y0, float[][] bm, int p, float[] col, float glow, float r) {
  Mask m = dotMask(bm, p, r);
  if (glow > 0) {
    int pad = 3 * p;
    Mask g = m.pad(pad).blur(p * 0.9);
    cv.composite((int) x0 - pad, (int) y0 - pad, col, g, glow);
  }
  cv.composite((int) x0, (int) y0, col, m);
  return cols(bm) * p;
}
int dm(Canvas cv, float x0, float y0, float[][] bm, int p, float[] col, float glow) { return dm(cv, x0, y0, bm, p, col, glow, DOT_R); }
int dm(Canvas cv, float x0, float y0, float[][] bm, int p, float[] col) { return dm(cv, x0, y0, bm, p, col, 0); }

// The glow comes from the whole-frame pass in Glow.pde, so text is drawn without its own.
int txt(Canvas cv, float x, float y, String s, String font, int p, float[] col) {
  return dm(cv, x, y, bitmap(s, font), p, col);
}

// text at a fractional dot pitch (e.g. 4.5): drawn at twice the pitch, then halved
int txtFine(Canvas cv, float x0, float y0, String s, String font, float p, float[] col) {
  if (p == round(p)) return txt(cv, x0, y0, s, font, round(p), col);
  float[][] bm = bitmap(s, font);
  Mask m = dotMask(bm, round(p * 2), DOT_R).half();
  cv.composite((int) x0, (int) y0, col, m);
  return round(cols(bm) * p);
}

// width including the last glyph's advance (for right-aligning, like the mockup)
int advWidth(String s, String font) {
  PixelFont pf = FONTS.get(font);
  int w = 0;
  for (int i = 0; i < s.length(); i++) w += advance(pf, s.charAt(i));
  return w;
}

int dmWidth(String s, String font, float p) { return s.length() == 0 ? 0 : round(cols(bitmap(s, font)) * p); }


// ---------- long titles: wrap onto two lines, then cut with "..." ----------
String ellipsize(String s, String font, float p, int maxw) {
  if (dmWidth(s, font, p) <= maxw) return s;
  String[] words = splitTokens(s, " ");
  for (int k = words.length - 1; k > 0; k--) {           // prefer cutting at a word boundary
    String cand = trimEnd(join(subset(words, 0, k), " "), ",.;:-") + "...";
    if (dmWidth(cand, font, p) <= maxw) return cand;
  }
  while (s.length() > 0 && dmWidth(s.trim() + "...", font, p) > maxw) s = s.substring(0, s.length() - 1);
  return s.trim() + "...";
}

String trimEnd(String s, String chars) {
  while (s.length() > 0 && chars.indexOf(s.charAt(s.length() - 1)) >= 0) s = s.substring(0, s.length() - 1);
  return s;
}

// fill up to maxLines lines word by word; whatever doesn't fit is cut with "..."
String[] wrapLines(String s, String font, float p, int maxw, int maxLines) {
  String[] words = splitTokens(s, " ");
  ArrayList<String> out = new ArrayList<String>();
  int i = 0;
  while (i < words.length && out.size() < maxLines) {
    String cur = words[i++];
    while (i < words.length && dmWidth(cur + " " + words[i], font, p) <= maxw) cur += " " + words[i++];
    if (out.size() == maxLines - 1 && i < words.length) cur = cur + " " + join(subset(words, i), " ");
    out.add(ellipsize(cur, font, p, maxw));
  }
  if (out.isEmpty()) out.add("");
  return out.toArray(new String[0]);
}

String[] wrapTitle(String s, String font, float p, int maxw) {
  String[] words = splitTokens(s.toUpperCase(), " ");
  String all = join(words, " ");
  if (dmWidth(all, font, p) <= maxw) return new String[] { all };
  // balanced two-line split if everything fits
  String[] best = null;
  int bestW = Integer.MAX_VALUE;
  for (int k = 1; k < words.length; k++) {
    String a = join(subset(words, 0, k), " "), b = join(subset(words, k), " ");
    int wa = dmWidth(a, font, p), wb = dmWidth(b, font, p);
    if (wa <= maxw && wb <= maxw && max(wa, wb) < bestW) { bestW = max(wa, wb); best = new String[] { a, b }; }
  }
  if (best != null) return best;
  // greedy fill of two lines, the rest gets cut
  ArrayList<String> out = new ArrayList<String>();
  String cur = "";
  int i = 0;
  while (i < words.length && out.size() < 2) {
    String trial = (cur + " " + words[i]).trim();
    if (dmWidth(trial, font, p) <= maxw) { cur = trial; i++; }
    else if (cur.length() == 0) { out.add(words[i]); i++; }
    else { out.add(cur); cur = ""; }
  }
  if (cur.length() > 0 && out.size() < 2) out.add(cur);
  if (i < words.length) {
    String last = (out.get(out.size() - 1) + " " + join(subset(words, i), " ")).trim();
    out.set(out.size() - 1, last);
  }
  String[] res = new String[out.size()];
  for (int k = 0; k < res.length; k++) res[k] = ellipsize(out.get(k), font, p, maxw);
  return res;
}
