// A float RGB canvas plus the few image operations the design needs:
// blending a colour (or image) through a soft mask, gaussian blur, and
// anti-aliased dot sprites.

class Canvas {
  int w, h;
  float[] r, g, b;

  Canvas(int w, int h) {
    this.w = w; this.h = h;
    r = new float[w * h]; g = new float[w * h]; b = new float[w * h];
  }

  Canvas copy() {
    Canvas c = new Canvas(w, h);
    arrayCopy(r, c.r); arrayCopy(g, c.g); arrayCopy(b, c.b);
    return c;
  }

  void fill(float[] col) {
    java.util.Arrays.fill(r, col[0]); java.util.Arrays.fill(g, col[1]); java.util.Arrays.fill(b, col[2]);
  }

  // blend a flat colour through mask m (mw x mh) placed at x0,y0
  void composite(int x0, int y0, float[] col, Mask m) { composite(x0, y0, col, m, 1); }

  void composite(int x0, int y0, float[] col, Mask m, float amount) {
    for (int y = max(0, y0); y < min(h, y0 + m.h); y++) {
      int my = y - y0;
      for (int x = max(0, x0); x < min(w, x0 + m.w); x++) {
        float a = m.v[my * m.w + (x - x0)] * amount;
        if (a <= 0) continue;
        if (a > 1) a = 1;
        int i = y * w + x;
        r[i] += (col[0] - r[i]) * a;
        g[i] += (col[1] - g[i]) * a;
        b[i] += (col[2] - b[i]) * a;
      }
    }
  }

  // blend another canvas (same size as the mask) through mask m
  void compositeImage(int x0, int y0, Canvas img, Mask m) {
    for (int y = max(0, y0); y < min(h, y0 + m.h); y++) {
      int my = y - y0;
      for (int x = max(0, x0); x < min(w, x0 + m.w); x++) {
        int mi = my * m.w + (x - x0);
        float a = m.v[mi];
        if (a <= 0) continue;
        int i = y * w + x;
        r[i] += (img.r[mi] - r[i]) * a;
        g[i] += (img.g[mi] - g[i]) * a;
        b[i] += (img.b[mi] - b[i]) * a;
      }
    }
  }

  // per-pixel lerp toward another full-size canvas, inside a rectangle
  void lerpFrom(Canvas o, float[] alpha, int x0, int y0, int x1, int y1) {
    for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) {
      int i = y * w + x;
      float a = alpha[i];
      if (a <= 0) continue;
      r[i] += (o.r[i] - r[i]) * a; g[i] += (o.g[i] - g[i]) * a; b[i] += (o.b[i] - b[i]) * a;
    }
  }

  // rows y0..y1 as a new full-width canvas
  Canvas copyRegion(int y0, int y1) {
    Canvas c = new Canvas(w, y1 - y0);
    int n = (y1 - y0) * w;
    System.arraycopy(r, y0 * w, c.r, 0, n); System.arraycopy(g, y0 * w, c.g, 0, n); System.arraycopy(b, y0 * w, c.b, 0, n);
    return c;
  }

  void copyRect(Canvas o, int x0, int y0, int x1, int y1) {
    for (int y = y0; y < y1; y++) {
      int i = y * w + x0, n = x1 - x0;
      System.arraycopy(o.r, i, r, i, n); System.arraycopy(o.g, i, g, i, n); System.arraycopy(o.b, i, b, i, n);
    }
  }

  int[] toPixels(int[] out) {
    if (out == null) out = new int[w * h];
    for (int i = 0; i < out.length; i++) {
      int R = (int) constrain(r[i], 0, 255), G = (int) constrain(g[i], 0, 255), B = (int) constrain(b[i], 0, 255);
      out[i] = 0xFF000000 | (R << 16) | (G << 8) | B;
    }
    return out;
  }
}


// A soft alpha mask (0..1)
class Mask {
  int w, h;
  float[] v;
  Mask(int w, int h) { this.w = w; this.h = h; v = new float[w * h]; }

  Mask copy() { Mask m = new Mask(w, h); arrayCopy(v, m.v); return m; }

  Mask pad(int p) {
    Mask m = new Mask(w + 2 * p, h + 2 * p);
    for (int y = 0; y < h; y++) System.arraycopy(v, y * w, m.v, (y + p) * m.w + p, w);
    return m;
  }

  Mask blur(float sigma) { Mask m = copy(); gaussian(m.v, w, h, sigma); return m; }

  Mask times(float k) { Mask m = copy(); for (int i = 0; i < v.length; i++) m.v[i] *= k; return m; }
}


// ---------- gaussian blur (separable, in place) ----------
void gaussian(float[] a, int w, int h, float sigma) {
  if (sigma <= 0) return;
  int rad = ceil(sigma * 4);
  float[] k = new float[2 * rad + 1];
  float sum = 0;
  for (int i = -rad; i <= rad; i++) { k[i + rad] = exp(-(i * i) / (2 * sigma * sigma)); sum += k[i + rad]; }
  for (int i = 0; i < k.length; i++) k[i] /= sum;
  float[] tmp = new float[max(w, h)];
  // rows (edges reflect, like scipy)
  for (int y = 0; y < h; y++) {
    int o = y * w;
    for (int x = 0; x < w; x++) {
      float s = 0;
      for (int j = -rad; j <= rad; j++) s += a[o + reflect(x + j, w)] * k[j + rad];
      tmp[x] = s;
    }
    System.arraycopy(tmp, 0, a, o, w);
  }
  for (int x = 0; x < w; x++) {
    for (int y = 0; y < h; y++) {
      float s = 0;
      for (int j = -rad; j <= rad; j++) s += a[reflect(y + j, h) * w + x] * k[j + rad];
      tmp[y] = s;
    }
    for (int y = 0; y < h; y++) a[y * w + x] = tmp[y];
  }
}

int reflect(int i, int n) {
  while (i < 0 || i >= n) {
    if (i < 0) i = -i - 1;
    if (i >= n) i = 2 * n - i - 1;
  }
  return i;
}


// ---------- anti-aliased shapes ----------
HashMap<String, Mask> spriteCache = new HashMap<String, Mask>();

// one round (or square) dot centred in a p x p cell; r = radius as a fraction of p
Mask sprite(int p, float r, boolean square) {
  String key = p + ":" + r + ":" + square;
  if (spriteCache.containsKey(key)) return spriteCache.get(key);
  int ss = 8;
  Mask m = new Mask(p, p);
  float c = p / 2.0, rr = p * r;
  for (int y = 0; y < p; y++) for (int x = 0; x < p; x++) {
    int hit = 0;
    for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
      float px = x + (sx + 0.5) / ss - c, py = y + (sy + 0.5) / ss - c;
      if (square ? (abs(px) <= rr && abs(py) <= rr) : (px * px + py * py <= rr * rr)) hit++;
    }
    m.v[y * p + x] = hit / float(ss * ss);
  }
  spriteCache.put(key, m);
  return m;
}
Mask sprite(int p, float r) { return sprite(p, r, false); }

// a bitmap (rows x cols of 0/1) where every 1 becomes a dot sprite
Mask dotMask(float[][] bm, int p, float r) {
  int rows = bm.length, cols = rows > 0 ? bm[0].length : 0;
  Mask s = sprite(p, r);
  Mask m = new Mask(max(cols * p, 1), max(rows * p, 1));
  for (int j = 0; j < rows; j++) for (int i = 0; i < cols; i++) {
    float on = bm[j][i];
    if (on <= 0) continue;
    for (int y = 0; y < p; y++) for (int x = 0; x < p; x++) m.v[(j * p + y) * m.w + i * p + x] = s.v[y * p + x] * on;
  }
  return m;
}

// filled disc of radius rad, returned with its top-left corner
Mask disc(float rad) {
  int R = ceil(rad) + 3, N = 2 * R, ss = 3;
  Mask m = new Mask(N, N);
  for (int y = 0; y < N; y++) for (int x = 0; x < N; x++) {
    int hit = 0;
    for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
      float dx = x + (sx + 0.5) / ss - R, dy = y + (sy + 0.5) / ss - R;
      if (dx * dx + dy * dy <= rad * rad) hit++;
    }
    m.v[y * N + x] = hit / float(ss * ss);
  }
  return m;
}

// rounded rectangle mask
Mask roundRect(int w, int h, float rad) {
  int ss = 4;
  Mask m = new Mask(w, h);
  for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
    int hit = 0;
    for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
      float px = x + (sx + 0.5) / ss, py = y + (sy + 0.5) / ss;
      float cx = constrain(px, rad, w - rad), cy = constrain(py, rad, h - rad);
      if (sq(px - cx) + sq(py - cy) <= rad * rad) hit++;
    }
    m.v[y * w + x] = hit / float(ss * ss);
  }
  return m;
}
