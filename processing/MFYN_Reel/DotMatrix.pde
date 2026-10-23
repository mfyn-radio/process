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
    FONTS.put(key, pf);
  }
}

// render a string to a 0/1 bitmap (rows x cols), trailing empty columns trimmed
float[][] bitmap(String s, String font) {
  PixelFont pf = FONTS.get(font);
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
int dm(Canvas cv, float x0, float y0, float[][] bm, int p, float[] col, float glow) { return dm(cv, x0, y0, bm, p, col, glow, 0.40); }

int txt(Canvas cv, float x, float y, String s, String font, int p, float[] col, float glow) {
  return dm(cv, x, y, bitmap(s, font), p, col, glow);
}
int txt(Canvas cv, float x, float y, String s, String font, int p, float[] col) { return txt(cv, x, y, s, font, p, col, 0.55); }

int dmWidth(String s, String font, int p) { return s.length() == 0 ? 0 : cols(bitmap(s, font)) * p; }


// ---------- long titles: wrap onto two lines, then cut with "..." ----------
String ellipsize(String s, String font, int p, int maxw) {
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

String[] wrapTitle(String s, String font, int p, int maxw) {
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
