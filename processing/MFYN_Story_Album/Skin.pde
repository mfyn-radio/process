// The media player: silver frames, glossy buttons, album info, tracklist.
// Drawn once per album onto a Layer (colour + alpha), so the globe can show
// through everywhere the player isn't.

// ---------- palette ----------
final float[] B0 = { 28, 70, 160 }, B1 = { 110, 170, 235 };          // selection / seek blue
final float[] SIL0 = { 246, 247, 250 }, SIL1 = { 196, 201, 210 };    // frame silver
final float[] DARK = { 58, 64, 80 };                                 // frame outline
final float[] TXT = { 24, 30, 46 }, MUTE = { 110, 118, 134 }, LABEL = { 60, 68, 86 };
final float[] WHITE = { 255, 255, 255 };
final float[] STRIP0 = { 176, 182, 194 }, STRIP1 = { 214, 218, 226 }, GRIP = { 150, 156, 168 };

// ---------- layout (story safe zone: 250px top, 340px bottom) ----------
final int CS = 600;                       // cover size
final int UX0 = 60, UY0 = 320;            // player unit: art + controls + tracklist
final int UPAD = 20;
final int IX0 = 360, IY0 = 250, IX1 = 1050, IY1 = 890;   // album info panel, behind the player
final int EX = 600;                       // info panel shows above the player only right of this
final int ROW_H = 28, LIST_SIZE = 15, MAX_ROWS = 14;
final int PILL_H = 84;
// seek bar strip (redrawn every frame)
int SEEK_SX0, SEEK_SX1, SEEK_CY;
int SEEK_RX0, SEEK_RX1, SEEK_RY0, SEEK_RY1;

HashMap<String, PFont> fontCache = new HashMap<String, PFont>();
PGraphics measure;

void loadSkinFonts() {
  measure = createGraphics(16, 16);
}

PFont font(String file, float size) {
  String key = file + "@" + size;
  PFont f = fontCache.get(key);
  if (f == null) { f = createFont(dataPath(file), size, true); fontCache.put(key, f); }
  return f;
}
final String WIDE = "Michroma-Regular.ttf", PIXEL = "Silkscreen-Regular.ttf";


// ---------- an RGBA float canvas ----------
class Layer {
  int w, h;
  float[] r, g, b, a;
  Layer(int w, int h) { this.w = w; this.h = h; r = new float[w * h]; g = new float[w * h]; b = new float[w * h]; a = new float[w * h]; }
  Layer copy() {
    Layer o = new Layer(w, h);
    arrayCopy(r, o.r); arrayCopy(g, o.g); arrayCopy(b, o.b); arrayCopy(a, o.a);
    return o;
  }
  // paint colour c with coverage m over pixel i
  void over(int i, float cr, float cg, float cb, float m) {
    if (m <= 0) return;
    if (m > 1) m = 1;
    float na = a[i] + m * (1 - a[i]);
    float k = a[i] * (1 - m);
    r[i] = (r[i] * k + cr * m) / na;
    g[i] = (g[i] * k + cg * m) / na;
    b[i] = (b[i] * k + cb * m) / na;
    a[i] = na;
  }
  void fillRect(int x0, int y0, int x1, int y1, float[] c) {
    for (int y = max(0, y0); y < min(h, y1); y++) for (int x = max(0, x0); x < min(w, x1); x++) {
      int i = y * w + x; r[i] = c[0]; g[i] = c[1]; b[i] = c[2]; a[i] = 1;
    }
  }
  void clearRect(int x0, int y0, int x1, int y1) {
    for (int y = max(0, y0); y < min(h, y1); y++) for (int x = max(0, x0); x < min(w, x1); x++) a[y * w + x] = 0;
  }
  void copyRect(Layer o, int x0, int y0, int x1, int y1) {
    for (int y = y0; y < y1; y++) {
      int i = y * w + x0, n = x1 - x0;
      System.arraycopy(o.r, i, r, i, n); System.arraycopy(o.g, i, g, i, n);
      System.arraycopy(o.b, i, b, i, n); System.arraycopy(o.a, i, a, i, n);
    }
  }
}

// an anti-aliased coverage mask placed at (x, y)
class MaskAt {
  int x, y, w, h;
  float[] v;
  MaskAt(int x, int y, int w, int h) { this.x = x; this.y = y; this.w = max(1, w); this.h = max(1, h); v = new float[this.w * this.h]; }
}

PGraphics maskCanvas(int w, int h) {
  PGraphics pg = createGraphics(max(1, w), max(1, h));
  pg.beginDraw();
  pg.background(0);
  pg.noStroke();
  pg.fill(255);
  return pg;
}

MaskAt fromCanvas(PGraphics pg, int x, int y) {
  pg.endDraw();
  pg.loadPixels();
  MaskAt m = new MaskAt(x, y, pg.width, pg.height);
  for (int i = 0; i < m.v.length; i++) m.v[i] = (pg.pixels[i] & 0xFF) / 255.0;
  return m;
}

MaskAt rrMask(float x0, float y0, float x1, float y1, float rad) {
  int ox = (int) x0 - 2, oy = (int) y0 - 2;
  PGraphics pg = maskCanvas((int) x1 + 2 - ox, (int) y1 + 2 - oy);
  pg.rect(x0 - ox, y0 - oy, x1 - x0, y1 - y0, rad);
  return fromCanvas(pg, ox, oy);
}

MaskAt polyMask(float[] xs, float[] ys, int padLo, int padHi) {
  float mnx = min(xs), mny = min(ys), mxx = max(xs), mxy = max(ys);
  int ox = (int) mnx - padLo, oy = (int) mny - padLo;
  PGraphics pg = maskCanvas((int) mxx + padHi - ox, (int) mxy + padHi - oy);
  pg.beginShape();
  for (int i = 0; i < xs.length; i++) pg.vertex(xs[i] - ox, ys[i] - oy);
  pg.endShape(CLOSE);
  return fromCanvas(pg, ox, oy);
}

float textW(String file, float size, String s, float sp) {
  measure.beginDraw();
  measure.textFont(font(file, size));
  float w = 0;
  for (int i = 0; i < s.length(); i++) w += measure.textWidth(s.charAt(i));
  measure.endDraw();
  return w + sp * max(0, s.length() - 1);
}

MaskAt textMask(float x, float yb, String s, String file, float size, float sp) {
  int wdt = (int) textW(file, size, s, sp) + 40;
  int ox = (int) x - 20, oy = (int) (yb - size * 1.3);
  PGraphics pg = maskCanvas(wdt, (int) (yb + size * 0.5) - oy);
  pg.textFont(font(file, size));
  pg.textAlign(LEFT, BASELINE);
  float X = x - ox;
  for (int i = 0; i < s.length(); i++) {
    char c = s.charAt(i);
    pg.text(c, X, yb - oy);
    X += pg.textWidth(c) + sp;
  }
  return fromCanvas(pg, ox, oy);
}


// ---------- painting ----------
void paint(Layer L, MaskAt m, float[] col, float k) {
  for (int y = 0; y < m.h; y++) {
    int gy = m.y + y;
    if (gy < 0 || gy >= L.h) continue;
    for (int x = 0; x < m.w; x++) {
      int gx = m.x + x;
      if (gx < 0 || gx >= L.w) continue;
      L.over(gy * L.w + gx, col[0], col[1], col[2], m.v[y * m.w + x] * k);
    }
  }
}

// vertical (or horizontal) gradient through a mask, with an optional glossy top highlight
void gradFill(Layer L, MaskAt m, float[] c0, float[] c1, boolean horiz, float gloss) {
  for (int y = 0; y < m.h; y++) {
    int gy = m.y + y;
    if (gy < 0 || gy >= L.h) continue;
    float ty = m.h > 1 ? y / (float) (m.h - 1) : 0;
    float hl = gloss > 0 ? pow(max(0, 1 - ty / 0.48), 0.7) * gloss : 0;
    for (int x = 0; x < m.w; x++) {
      int gx = m.x + x;
      if (gx < 0 || gx >= L.w) continue;
      float mv = m.v[y * m.w + x];
      if (mv <= 0) continue;
      float t = horiz ? (m.w > 1 ? x / (float) (m.w - 1) : 0) : ty;
      float r = c0[0] + (c1[0] - c0[0]) * t, g = c0[1] + (c1[1] - c0[1]) * t, b = c0[2] + (c1[2] - c0[2]) * t;
      r += (255 - r) * hl; g += (255 - g) * hl; b += (255 - b) * hl;
      L.over(gy * L.w + gx, r, g, b, mv);
    }
  }
}

// thin dark line just inside a shape's edge
void edge(Layer L, MaskAt m, float[] col) {
  float[] bl = m.v.clone();
  gaussian(bl, m.w, m.h, 2);
  MaskAt e = new MaskAt(m.x, m.y, m.w, m.h);
  for (int i = 0; i < e.v.length; i++) e.v[i] = constrain(m.v[i] - constrain(bl[i] * 1.6 - 0.6, 0, 1), 0, 1) * 0.9;
  paint(L, e, col, 1);
}

void panelRR(Layer L, float x0, float y0, float x1, float y1, float rad, float[] c0, float[] c1, float gloss, boolean horiz, float[] border) {
  MaskAt m = rrMask(x0, y0, x1, y1, rad);
  gradFill(L, m, c0, c1, horiz, gloss);
  if (border != null) edge(L, m, border);
}

void putText(Layer L, float x, float yb, String s, String file, float size, float[] col, float sp) {
  paint(L, textMask(x, yb, s, file, size, sp), col, 1);
}

void polyFill(Layer L, float[] xs, float[] ys, float[] col) {
  paint(L, polyMask(xs, ys, 3, 4), col, 1);
}

// silver window frame with one cut corner (bottom right)
void frame(Layer L, float x0, float y0, float x1, float y1, float cut) {
  float[] xs = { x0, x1, x1, x1 - cut, x0 }, ys = { y0, y0, y1 - cut, y1, y1 };
  paint(L, polyMask(xs, ys, 2, 3), DARK, 1);
  float[] xi = { x0 + 3, x1 - 3, x1 - 3, x1 - cut - 1, x0 + 3 }, yi = { y0 + 3, y0 + 3, y1 - cut - 1, y1 - 3, y1 - 3 };
  gradFill(L, polyMask(xi, yi, 2, 3), SIL0, SIL1, false, 0);
  L.fillRect((int) x0 + 3, (int) y0 + 3, (int) x1 - 3, (int) y0 + 5, WHITE);
}

// grey title strip with grip lines and a label
void titleStrip(Layer L, int x0, int y0, int x1, int labelX, String label, int lines) {
  gradFill(L, rrMask(x0 + 10, y0 + 10, x1 - 10, y0 + 44, 6), STRIP0, STRIP1, true, 0);
  for (int k = 0; k < lines; k++) L.fillRect(x0 + 20 + 9 * k, y0 + 20, x0 + 22 + 9 * k, y0 + 34, GRIP);
  putText(L, labelX, y0 + 33, label, PIXEL, 14, LABEL, 3);
}

void roundBtn(Layer L, float cx, float cy, float r, String glyph, boolean big) {
  MaskAt m = rrMask(cx - r, cy - r, cx + r, cy + r, r);
  gradFill(L, m, new float[] { 252, 253, 255 }, new float[] { 170, 178, 192 }, false, 0.5);
  edge(L, m, new float[] { 120, 128, 142 });
  float s = r * 0.42;
  float[] col = big ? B0 : new float[] { 60, 70, 92 };
  if (glyph.equals("play")) {
    polyFill(L, new float[] { cx - s * 0.6, cx + s, cx - s * 0.6 }, new float[] { cy - s, cy, cy + s }, col);
  } else if (glyph.equals("pause")) {
    float bw = s * 0.6, bh = s * 0.85, gap = s * 0.2;
    paint(L, rrMask(cx - gap - bw, cy - bh, cx - gap, cy + bh, 2), col, 1);
    paint(L, rrMask(cx + gap, cy - bh, cx + gap + bw, cy + bh, 2), col, 1);
  } else if (glyph.equals("stop")) {
    L.fillRect((int) (cx - s * 0.7), (int) (cy - s * 0.7), (int) (cx + s * 0.7), (int) (cy + s * 0.7), col);
  } else if (glyph.equals("prev") || glyph.equals("next")) {
    float d = glyph.equals("prev") ? -1 : 1;
    polyFill(L, new float[] { cx - d * s * 0.8, cx + d * s * 0.3, cx - d * s * 0.8 }, new float[] { cy - s * 0.8, cy, cy + s * 0.8 }, col);
    int bx = (int) (cx + d * s * 0.45);
    L.fillRect(bx - 3, (int) (cy - s * 0.8), bx + 3, (int) (cy + s * 0.8), col);
  }
}

// the pill: pause, stop, prev, next, seek bar, volume wedge
void progressPill(Layer L, float x0, float y, float x1, float h) {
  panelRR(L, x0, y, x1, y + h, (int) h / 2, new float[] { 250, 251, 253 }, new float[] { 186, 192, 204 }, 0.45, false, new float[] { 140, 148, 162 });
  float cy = y + (int) h / 2, k = h / 108.0;
  float bx = x0 + 64 * k;
  roundBtn(L, bx, cy, 42 * k, "pause", true);     // the track is playing
  float bx2 = bx + 94 * k;
  String[] g = { "stop", "prev", "next" };
  for (String s : g) { roundBtn(L, bx2, cy, 28 * k, s, false); bx2 += 66 * k; }
  SEEK_SX0 = (int) (bx2 + 6); SEEK_SX1 = (int) (x1 - 200 * k); SEEK_CY = (int) cy;
  panelRR(L, SEEK_SX0, cy - 10, SEEK_SX1, cy + 10, 10, new float[] { 150, 158, 172 }, new float[] { 230, 234, 240 }, 0, false, new float[] { 120, 128, 140 });
  SEEK_RX0 = SEEK_SX0 - 22; SEEK_RX1 = SEEK_SX1 + 22; SEEK_RY0 = SEEK_CY - 24; SEEK_RY1 = SEEK_CY + 24;
  float vx0 = x1 - 160 * k, vx1 = x1 - 30 * k;
  polyFill(L, new float[] { vx0, vx1, vx1 }, new float[] { cy + 16, cy - 14, cy + 16 }, new float[] { 190, 196, 206 });
  float vm = vx0 + (vx1 - vx0) * 0.7;
  polyFill(L, new float[] { vx0, vm, vm }, new float[] { cy + 16, cy - 5, cy + 16 }, new float[] { 120, 220, 80 });
}

// blue fill + knob at frac (0..1) of the seek bar
void drawSeek(Layer L, float frac) {
  float a = SEEK_SX0 + 4, b = SEEK_SX1 - 4;
  float fx = a + (b - a) * frac;
  if (fx - a > 8) panelRR(L, a, SEEK_CY - 6, round(fx), SEEK_CY + 6, 6, B1, B0, 0, false, null);
  roundBtn(L, fx, SEEK_CY, 16, "", false);
}

// one labelled field in the album info panel; returns the y below it
float field(Layer L, float fx0, float fy, float fx1, String lab, String val, float size, int maxLines) {
  putText(L, fx0, fy + 16, lab, PIXEL, 14, MUTE, 3);
  ArrayList<String> lines = wrapWords(val, size, fx1 - fx0 - 30, maxLines);
  float hgt = 22 + (size + 17) * lines.size();
  panelRR(L, fx0, fy + 26, fx1, fy + 26 + hgt, 8, WHITE, new float[] { 238, 241, 246 }, 0, false, new float[] { 150, 158, 172 });
  for (int j = 0; j < lines.size(); j++) putText(L, fx0 + 14, fy + 26 + 20 + size + j * (size + 17), lines.get(j), WIDE, size, TXT, 1);
  return fy + 26 + hgt;
}

ArrayList<String> wrapWords(String text, float size, float maxw, int maxLines) {
  ArrayList<String> lines = new ArrayList<String>();
  String cur = "";
  for (String w : text.split("\\s+")) {
    String t = (cur + " " + w).trim();
    if (textW(WIDE, size, t, 1) <= maxw || cur.length() == 0) cur = t;
    else { lines.add(cur); cur = w; }
  }
  lines.add(cur);
  while (lines.size() > maxLines) {
    String last = lines.remove(lines.size() - 1);
    lines.set(lines.size() - 1, lines.get(lines.size() - 1) + " " + last);
  }
  int li = lines.size() - 1;
  lines.set(li, fitText(lines.get(li), WIDE, size, maxw, 1));
  for (int i = 0; i < li; i++) lines.set(i, fitText(lines.get(i), WIDE, size, maxw, 1));
  return lines;
}

String fitText(String s, String file, float size, float maxw, float sp) {
  if (textW(file, size, s, sp) <= maxw) return s;
  String dots = font(file, size).getNative() != null && ((java.awt.Font) font(file, size).getNative()).canDisplay('…') ? "…" : "...";
  while (s.length() > 0 && textW(file, size, s + dots, sp) > maxw) s = s.substring(0, s.length() - 1);
  return s.trim() + dots;
}

// soft shadow from the player's right edge, only onto the info panel underneath
void contactShadow(Layer L, int x0, int y0, int x1, int y1, int rx0, int ry0, int rx1, int ry1) {
  int pad = 40;
  int ax = rx0 - pad, ay = ry0 - pad, w = rx1 - rx0 + 2 * pad, h = ry1 - ry0 + 2 * pad;
  float[] m = new float[w * h];
  for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
    int gx = ax + x, gy = ay + y;
    if (gx >= x0 && gx < x1 && gy >= y0 && gy < y1) m[y * w + x] = 1;
  }
  float[] s = m.clone();
  gaussian(s, w, h, 9);
  for (int y = ry0; y < ry1; y++) for (int x = rx0; x < rx1; x++) {
    int li = (y - ay) * w + (x - ax), sx = x - 6 - ax;            // shifted 6px right
    float sh = sx >= 0 ? s[(y - ay) * w + sx] : 0;
    float a = sh * (1 - m[li]) * 0.55;
    if (a <= 0) continue;
    int i = y * L.w + x;
    L.r[i] = L.r[i] * (1 - a) + 30 * a; L.g[i] = L.g[i] * (1 - a) + 34 * a; L.b[i] = L.b[i] * (1 - a) + 46 * a;
  }
}

// centre-square crop, area-averaged to S x S
float[][] coverPixels(PImage src, int S) {
  int m = min(src.width, src.height);
  int ox = (src.width - m) / 2, oy = (src.height - m) / 2;
  PImage sq = src.get(ox, oy, m, m);
  if (m < S) { sq.resize(S, S); m = S; }
  sq.loadPixels();
  float[][] out = new float[3][S * S];
  for (int j = 0; j < S; j++) for (int i = 0; i < S; i++) {
    int xa = i * m / S, xb = max(xa + 1, (i + 1) * m / S), ya = j * m / S, yb = max(ya + 1, (j + 1) * m / S);
    float r = 0, g = 0, b = 0; int n = 0;
    for (int y = ya; y < yb; y++) for (int x = xa; x < xb; x++) {
      int c = sq.pixels[y * m + x];
      r += (c >> 16) & 255; g += (c >> 8) & 255; b += c & 255; n++;
    }
    out[0][j * S + i] = r / n; out[1][j * S + i] = g / n; out[2][j * S + i] = b / n;
  }
  return out;
}


// ---------- the whole player ----------
Layer buildPlayer(Album al, PImage cover) {
  Layer L = new Layer(W, H);
  int coverW = CS + 60;

  // album info panel (behind)
  int fx0 = UX0 + coverW + 20;
  frame(L, IX0, IY0, IX1, IY1, 30);
  gradFill(L, rrMask(IX0 + 10, IY0 + 10, IX1 - 10, IY0 + 44, 6), STRIP0, STRIP1, true, 0);
  for (int k = 0; k < IX1 - IX0 - 40; k += 9) L.fillRect(IX0 + 20 + k, IY0 + 20, IX0 + 22 + k, IY0 + 34, GRIP);
  L.fillRect(fx0 - 8, IY0 + 18, IX1 - 18, IY0 + 36, STRIP1);
  putText(L, fx0, IY0 + 33, "ALBUM INFO", PIXEL, 14, LABEL, 3);
  float fy = IY0 + 44;
  fy = field(L, fx0, fy, IX1 - 20, "TITLE", al.album.toUpperCase(), 17, 4) + 10;
  fy = field(L, fx0, fy, IX1 - 20, "ARTIST", al.artist.toUpperCase(), 17, 2) + 10;
  if (al.released.length() > 0) fy = field(L, fx0, fy, IX1 - 20, "RELEASED", al.released, 17, 1) + 10;
  fy = field(L, fx0, fy, IX1 - 20, "TRACKS", str(al.tracks.size()), 17, 1) + 10;

  contactShadow(L, UX0, UY0, UX0 + coverW, H, IX0, IY0, IX1, IY1);
  // the info panel only shows above the player to the right of EX
  L.clearRect(IX0 - 2, IY0 - 2, EX + 2, UY0 + 2);
  L.fillRect(EX - 3, IY0, EX, UY0, DARK);
  L.fillRect(EX, IY0 + 3, EX + 2, UY0, WHITE);

  // player unit: art, pill, tracklist in one frame
  int x0 = UX0, x1 = UX0 + CS + 2 * UPAD + 20;
  int sy = UY0, y0 = UY0 + 34;
  int ay1 = y0 + CS + UPAD + 20, py = ay1 + 14, ty0 = py + PILL_H + 14;
  int n = al.tracks.size(), rows = min(n, MAX_ROWS);
  int first = constrain(al.featuredIdx - rows / 2, 0, n - rows);   // long albums: a window around the featured track
  int ty1 = ty0 + 18 + ROW_H * rows + 14, y1 = ty1 + UPAD;
  frame(L, x0, sy, x1, y1, 30);
  titleStrip(L, x0, sy, x1, x0 + 20 + 14 * 9 + 1, "NOW PLAYING", 14);
  panelRR(L, x0 + UPAD, y0 + UPAD, x1 - UPAD, ay1, 10, new float[] { 8, 12, 24 }, new float[] { 22, 30, 56 }, 0, false, new float[] { 110, 118, 132 });
  float[][] art = coverPixels(cover, CS);
  int axp = x0 + UPAD + 10, ayp = y0 + UPAD + 10;
  for (int y = 0; y < CS; y++) for (int x = 0; x < CS; x++) {
    int i = (ayp + y) * W + axp + x, k = y * CS + x;
    L.r[i] = art[0][k]; L.g[i] = art[1][k]; L.b[i] = art[2][k]; L.a[i] = 1;
  }
  progressPill(L, x0 + UPAD, py, x1 - UPAD, PILL_H);
  panelRR(L, x0 + UPAD, ty0, x1 - UPAD, ty1, 10, WHITE, new float[] { 246, 248, 251 }, 0, false, new float[] { 150, 158, 172 });
  int ry = ty0 + 16;
  for (int r = 0; r < rows; r++) {
    int i = first + r;
    boolean sel = i == al.featuredIdx;
    if (sel) gradFill(L, rrMask(x0 + UPAD + 6, ry, x1 - UPAD - 6, ry + ROW_H, 6), B1, B0, true, 0.3);
    Track t = al.tracks.get(i);
    int num = t.number > 0 ? t.number : i + 1;
    putText(L, x0 + UPAD + 24, ry + ROW_H - 6, nf(num, 2), PIXEL, 14, sel ? WHITE : MUTE, 2);
    putText(L, x0 + UPAD + 74, ry + ROW_H - 6, fitText(t.title.toUpperCase(), WIDE, LIST_SIZE, x1 - x0 - 2 * UPAD - 104, 1), WIDE, LIST_SIZE, sel ? WHITE : TXT, 1);
    ry += ROW_H;
  }
  return L;
}
