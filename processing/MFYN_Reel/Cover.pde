// Album cover treatment:
//   1. centre-crop to a square, reduce to 4px blocks
//   2. orange scale (brightness mapped onto the player's palette)
//   3. auto-level so every cover lands at the same average brightness
//   4. LED texture + soft bloom, dimmed, with a faint dot-matrix overlay

float COVER_TARGET = 0.30;     // average brightness after auto-levelling
float COVER_DIM    = 0.58;
int   COVER_BLOCK  = 4;

Canvas treatCover(PImage src, int S) {
  // 1. centre square, area-average down to S/BLOCK
  int m = min(src.width, src.height);
  int ox = (src.width - m) / 2, oy = (src.height - m) / 2;
  int n = S / COVER_BLOCK;
  src.loadPixels();
  float[] L = new float[n * n];
  for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) {
    int xa = ox + i * m / n, xb = ox + (i + 1) * m / n, ya = oy + j * m / n, yb = oy + (j + 1) * m / n;
    float sr = 0, sg = 0, sb = 0; int cnt = 0;
    for (int y = ya; y < max(yb, ya + 1); y++) for (int x = xa; x < max(xb, xa + 1); x++) {
      int c = src.pixels[y * src.width + x];
      sr += (c >> 16) & 255; sg += (c >> 8) & 255; sb += c & 255; cnt++;
    }
    // 2. luminance, slight contrast lift
    float lum = (0.299 * sr + 0.587 * sg + 0.114 * sb) / cnt / 255.0;
    L[j * n + i] = constrain((lum - 0.5) * 1.25 + 0.5, 0, 1);
  }

  // 3. auto-level: pick the gamma that puts the mean brightness at COVER_TARGET
  float bestG = 1, bestErr = Float.MAX_VALUE;
  for (int k = 0; k <= 180; k++) {
    float gm = 0.4 + 3.6 * k / 180.0, s = 0;
    for (int i = 0; i < L.length; i++) s += pow(L[i], gm);
    float err = abs(s / L.length - COVER_TARGET);
    if (err < bestErr) { bestErr = err; bestG = gm; }
  }
  for (int i = 0; i < L.length; i++) L[i] = pow(L[i], bestG);

  // orange ramp, blown back up to S x S in hard blocks
  Canvas c = new Canvas(S, S);
  for (int y = 0; y < S; y++) for (int x = 0; x < S; x++) {
    float l = L[min(y / COVER_BLOCK, n - 1) * n + min(x / COVER_BLOCK, n - 1)];
    float[] col = ramp(l);
    int i = y * S + x;
    c.r[i] = col[0]; c.g[i] = col[1]; c.b[i] = col[2];
  }

  // 4. LED texture (3px), bloom
  Mask led = sprite(3, 0.55);
  for (int y = 0; y < S; y++) for (int x = 0; x < S; x++) {
    float k = 1 - 0.35 + 0.35 * led.v[(y % 3) * 3 + (x % 3)];
    int i = y * S + x;
    c.r[i] *= k; c.g[i] *= k; c.b[i] *= k;
  }
  float[][] ch = { c.r, c.g, c.b };
  for (float[] a : ch) {
    float[] bl = new float[a.length];
    for (int i = 0; i < a.length; i++) bl[i] = max(a[i] - 120, 0);
    gaussian(bl, S, S, 4);
    for (int i = 0; i < a.length; i++) a[i] = constrain(a[i] + bl[i] * 0.45, 0, 255);
  }

  // dim + 6px dot-matrix overlay at low opacity
  Mask dots = sprite(6, 0.40);
  float OP = 0.28;
  for (int y = 0; y < S; y++) for (int x = 0; x < S; x++) {
    float d = dots.v[(y % 6) * 6 + (x % 6)];
    int i = y * S + x;
    for (int k = 0; k < 3; k++) {
      float v = ch[k][i] * COVER_DIM;
      v = v * (1 - OP) + v * (0.35 + 1.15 * d) * OP + OR[k] * d * 0.05;
      ch[k][i] = constrain(v, 0, 255);
    }
  }
  return c;
}

float[] ramp(float l) {
  float[] xs = { 0, 0.35, 0.70, 1 };
  float[][] cs = { BG, { 110, 34, 10 }, OR, LT };
  for (int k = 0; k < 3; k++) {
    if (l <= xs[k + 1]) {
      float t = (l - xs[k]) / (xs[k + 1] - xs[k]);
      return new float[] { lerp(cs[k][0], cs[k + 1][0], t), lerp(cs[k][1], cs[k + 1][1], t), lerp(cs[k][2], cs[k + 1][2], t) };
    }
  }
  return LT;
}

// glow behind, the treated cover, and its dotted frame
void drawCover(Canvas cv, Canvas art) {
  int S = art.w, x0 = COVER_CX - S / 2, y0 = COVER_CY - S / 2;
  Mask g = new Mask(S + 80, S + 80);
  for (int y = 40; y < S + 40; y++) for (int x = 40; x < S + 40; x++) g.v[y * g.w + x] = 1;
  cv.composite(x0 - 40, y0 - 40, OR, g.blur(14), 0.10);
  cv.compositeImage(x0, y0, art, roundRect(S, S, 10));
  dottedRect(cv, x0 - 14, y0 - 14, x0 + S + 14, y0 + S + 14, 18, 7, 2.2, OR, 0.45);
}
