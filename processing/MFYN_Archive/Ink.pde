// The type, and black ink that sits in the paper: soft edges, a little
// dropout where the grain is, and tinted by the paper brightness underneath.

PFont wordmarkFont, smallFont;

void loadFonts() {
  // Large sizes so the native font is used and stays crisp at any scale.
  wordmarkFont = createFont(dataPath(WORDMARK_FONT), WORDMARK_SIZE * 4, true);
  smallFont = createFont(dataPath(SMALL_FONT), SMALL_SIZE * 4, true);
}

// One line of text: font, size, tracking (1080 space), the pen's x and the baseline.
class Line {
  String text; PFont font; float size, track, x, baseline;
  Line(String text, PFont font, float size, float track, float x, float baseline) {
    this.text = text; this.font = font; this.size = size; this.track = track; this.x = x; this.baseline = baseline;
  }
}

// Width of a tracked line in 1080 space: every glyph's advance plus tracking, minus the last tracking.
float trackedWidth(String s, PFont font, float size, float track) {
  PGraphics g = measureG();
  g.textFont(font, size * SUPERSAMPLE);
  float w = 0;
  for (int i = 0; i < s.length(); i++) w += g.textWidth(s.charAt(i)) / SUPERSAMPLE + track;
  return w - track;
}

PGraphics measure;
PGraphics measureG() {
  if (measure == null) { measure = createGraphics(16, 16); measure.beginDraw(); measure.endDraw(); }
  return measure;
}

// A coverage mask (0..1) of these lines at S x S. The text is drawn SUPERSAMPLE
// times larger, glyph by glyph with no kerning, in a band just around the lines,
// then averaged down.
float[] textMask(Line[] lines, int S, float top, float bottom) {
  int k = S / B, ss = SUPERSAMPLE;
  int y0 = max(0, floor(top)), y1 = min(B, ceil(bottom));
  int bw = S * ss, bh = (y1 - y0) * k * ss;
  PGraphics g = createGraphics(bw, bh);
  g.smooth(8);
  g.beginDraw();
  g.background(0);
  g.noStroke();
  g.fill(255);
  for (Line l : lines) {
    g.textFont(l.font, l.size * k * ss);
    float x = l.x * k * ss, y = (l.baseline - y0) * k * ss;
    for (int i = 0; i < l.text.length(); i++) {
      char ch = l.text.charAt(i);
      g.text(ch, x, y);
      x += g.textWidth(ch) + l.track * k * ss;
    }
  }
  g.endDraw();
  g.loadPixels();
  float[] m = new float[S * S];
  int rows = (y1 - y0) * k;
  for (int y = 0; y < rows; y++) for (int x = 0; x < S; x++) {
    float s = 0;
    for (int dy = 0; dy < ss; dy++) for (int dx = 0; dx < ss; dx++) s += g.pixels[(y * ss + dy) * bw + x * ss + dx] & 255;
    m[(y0 * k + y) * S + x] = s / (255.0 * ss * ss);
  }
  return m;
}

// Lay ink through mask m onto img (in place).
void applyInk(java.util.Random rng, float[][] img, float[] m, int S) {
  int k = S / B;
  gaussian(m, S, S, INK_SPREAD * k);
  float[] grain = noise(rng, 0.5, 0.5, true);
  gaussian(grain, B, B, GRAIN_BLUR);
  float lo = Float.MAX_VALUE, hi = -Float.MAX_VALUE;
  for (float v : grain) { lo = min(lo, v); hi = max(hi, v); }
  for (int i = 0; i < grain.length; i++) grain[i] = (grain[i] - lo) / (hi - lo);
  grain = upscale(grain, S);
  for (int i = 0; i < m.length; i++) {
    if (m[i] <= 0) continue;
    float g = grain[i];
    float cover = constrain(m[i] * (1 - INK_DROPOUT * (g > GRAIN_THRESHOLD ? 1 : 0) * 0.9 - INK_DROPOUT * 0.3 * g), 0, 1);
    float lum = (img[0][i] + img[1][i] + img[2][i]) / 3 / PAPER_REF;
    for (int c = 0; c < 3; c++) {
      float tinted = INK[c] * (INK_FLOOR + INK_PAPER * lum);
      img[c][i] = img[c][i] * (1 - cover) + tinted * cover;
    }
  }
}
