// Float images and the few operations the cover needs: noise, a true
// (separable) Gaussian blur and a bicubic upscale.

// B x B normal noise. clip01 keeps it in 0..1, like the 8-bit images the
// reference blurs.
float[] noise(java.util.Random rng, float mean, float sd, boolean clip01) {
  float[] a = new float[B * B];
  for (int i = 0; i < a.length; i++) {
    float v = mean + sd * (float) rng.nextGaussian();
    a[i] = clip01 ? constrain(v, 0, 1) : v;
  }
  return a;
}

float mean(float[] a) {
  double s = 0;
  for (float v : a) s += v;
  return (float) (s / a.length);
}

// Gaussian blur in place, sigma in pixels, edges clamped.
void gaussian(float[] a, int w, int h, float sigma) {
  if (sigma <= 0) return;
  int r = max(1, ceil(sigma * 3));
  float[] k = new float[2 * r + 1];
  float sum = 0;
  for (int i = -r; i <= r; i++) { k[i + r] = exp(-(i * i) / (2 * sigma * sigma)); sum += k[i + r]; }
  for (int i = 0; i < k.length; i++) k[i] /= sum;
  float[] tmp = new float[max(w, h)];
  for (int y = 0; y < h; y++) {
    int o = y * w;
    for (int x = 0; x < w; x++) {
      float s = 0;
      for (int j = -r; j <= r; j++) s += a[o + min(w - 1, max(0, x + j))] * k[j + r];
      tmp[x] = s;
    }
    System.arraycopy(tmp, 0, a, o, w);
  }
  for (int x = 0; x < w; x++) {
    for (int y = 0; y < h; y++) {
      float s = 0;
      for (int j = -r; j <= r; j++) s += a[min(h - 1, max(0, y + j)) * w + x] * k[j + r];
      tmp[y] = s;
    }
    for (int y = 0; y < h; y++) a[y * w + x] = tmp[y];
  }
}

// B x B field to S x S, bicubic (Catmull-Rom), so a larger render keeps the
// same grain instead of getting finer grain.
float[] upscale(float[] a, int S) {
  if (S == B) return a;
  float[] out = new float[S * S];
  float f = B / (float) S;
  for (int y = 0; y < S; y++) {
    float sy = (y + 0.5) * f - 0.5;
    int y0 = floor(sy);
    float ty = sy - y0;
    for (int x = 0; x < S; x++) {
      float sx = (x + 0.5) * f - 0.5;
      int x0 = floor(sx);
      float tx = sx - x0, v = 0;
      for (int j = -1; j <= 2; j++) {
        float wy = cubic(j - ty);
        int yy = min(B - 1, max(0, y0 + j));
        for (int i = -1; i <= 2; i++) v += a[yy * B + min(B - 1, max(0, x0 + i))] * cubic(i - tx) * wy;
      }
      out[y * S + x] = v;
    }
  }
  return out;
}

float cubic(float t) {
  t = abs(t);
  if (t < 1) return 1.5 * t * t * t - 2.5 * t * t + 1;
  if (t < 2) return -0.5 * t * t * t + 2.5 * t * t - 4 * t + 2;
  return 0;
}
