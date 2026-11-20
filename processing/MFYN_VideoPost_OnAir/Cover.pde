// Album cover, "Screen" treatment: full colour, seen through the display's
// 6 px dot grid, slightly dimmed, with a soft bloom on the highlights.

float COVER_DIM   = 0.90;    // overall brightness of the cover
float COVER_BLOOM = 0.35;    // bloom strength on the highlights

Canvas treatCover(PImage src, int S) {
  // centre square, scaled to S x S (area average when shrinking)
  int m = min(src.width, src.height);
  int ox = (src.width - m) / 2, oy = (src.height - m) / 2;
  PImage sq = src.get(ox, oy, m, m);
  Canvas c = new Canvas(S, S);
  if (m < S) sq.resize(S, S);
  sq.loadPixels();
  int n = sq.width;
  for (int j = 0; j < S; j++) for (int i = 0; i < S; i++) {
    int xa = i * n / S, xb = max((i + 1) * n / S, xa + 1), ya = j * n / S, yb = max((j + 1) * n / S, ya + 1);
    float sr = 0, sg = 0, sb = 0; int cnt = 0;
    for (int y = ya; y < yb; y++) for (int x = xa; x < xb; x++) {
      int col = sq.pixels[y * n + x];
      sr += (col >> 16) & 255; sg += (col >> 8) & 255; sb += col & 255; cnt++;
    }
    int k = j * S + i;
    c.r[k] = sr / cnt; c.g[k] = sg / cnt; c.b[k] = sb / cnt;
  }

  // the dot grid: each 6 px cell is brightest in its centre
  for (int y = 0; y < S; y++) for (int x = 0; x < S; x++) {
    float d = dist(x % 6, y % 6, 2.5, 2.5) / 3.0 * 0.55;
    float g = constrain(1.25 - d, 0.55, 1.0) * COVER_DIM;
    int k = y * S + x;
    c.r[k] *= g; c.g[k] *= g; c.b[k] *= g;
  }

  // bloom on the highlights
  float[][] ch = { c.r, c.g, c.b };
  for (float[] a : ch) {
    float[] bl = new float[a.length];
    for (int i = 0; i < a.length; i++) bl[i] = max(a[i] - 150, 0);
    gaussian(bl, S, S, 4);
    for (int i = 0; i < a.length; i++) a[i] = constrain(a[i] + bl[i] * COVER_BLOOM, 0, 255);
  }
  return c;
}

// black behind the cover, the cover itself, and its dotted frame
void drawCover(Canvas cv, Canvas art) {
  int S = art.w, x0 = COVER_CX - S / 2, y0 = COVER_Y0;
  float[] black = { 0, 0, 0 };
  Mask clear = new Mask(S + 48, S + 48);
  java.util.Arrays.fill(clear.v, 1);
  cv.composite(x0 - 24, y0 - 24, black, clear);
  cv.compositeImage(x0, y0, art, roundRect(S, S, 10).blur(0.6));
  dottedRect(cv, x0 - 14, y0 - 14, x0 + S + 14, y0 + S + 14, 18, 7, 2.2, MID);
}
