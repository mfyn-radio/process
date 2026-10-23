// Blurs and the audio low-pass filter.

// gaussian blur (separable, in place, edges reflect)
void gaussian(float[] a, int w, int h, float sigma) {
  if (sigma <= 0) return;
  int rad = ceil(sigma * 4);
  float[] k = new float[2 * rad + 1];
  float sum = 0;
  for (int i = -rad; i <= rad; i++) { k[i + rad] = exp(-(i * i) / (2 * sigma * sigma)); sum += k[i + rad]; }
  for (int i = 0; i < k.length; i++) k[i] /= sum;
  float[] tmp = new float[max(w, h)];
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

// fast gaussian approximation for wide blurs: three box blurs
void blurBox3(float[] a, int w, int h, float sigma) {
  if (sigma <= 0) return;
  float wIdeal = sqrt(12 * sigma * sigma / 3 + 1);
  int wl = (int) floor(wIdeal);
  if (wl % 2 == 0) wl--;
  int wu = wl + 2;
  float mIdeal = (12 * sigma * sigma - 3 * wl * wl - 4 * 3 * wl - 3 * 3) / (-4.0 * wl - 4);
  int m = round(mIdeal);
  float[] tmp = new float[a.length];
  for (int i = 0; i < 3; i++) {
    int r = ((i < m ? wl : wu) - 1) / 2;
    boxH(a, tmp, w, h, r);
    boxV(tmp, a, w, h, r);
  }
}

void boxH(float[] src, float[] dst, int w, int h, int r) {
  float inv = 1.0 / (2 * r + 1);
  for (int y = 0; y < h; y++) {
    int o = y * w;
    float acc = 0;
    for (int x = -r - 1; x < r; x++) acc += src[o + constrain(x, 0, w - 1)];
    for (int x = 0; x < w; x++) {
      acc += src[o + min(x + r, w - 1)] - src[o + max(x - r - 1, 0)];
      dst[o + x] = acc * inv;
    }
  }
}

void boxV(float[] src, float[] dst, int w, int h, int r) {
  float inv = 1.0 / (2 * r + 1);
  for (int x = 0; x < w; x++) {
    float acc = 0;
    for (int y = -r - 1; y < r; y++) acc += src[constrain(y, 0, h - 1) * w + x];
    for (int y = 0; y < h; y++) {
      acc += src[min(y + r, h - 1) * w + x] - src[max(y - r - 1, 0) * w + x];
      dst[y * w + x] = acc * inv;
    }
  }
}

// 4th-order Butterworth low-pass, run forwards then backwards (zero phase)
float[] lowpass(float[] x, int sr, float fc) {
  float[] y = x.clone();
  float[] qs = { 0.54119610, 1.3065630 };
  for (int pass = 0; pass < 2; pass++) {
    for (float q : qs) biquadLP(y, sr, fc, q);
    reverseInPlace(y);
  }
  return y;
}

void reverseInPlace(float[] a) {
  for (int i = 0, j = a.length - 1; i < j; i++, j--) { float t = a[i]; a[i] = a[j]; a[j] = t; }
}

void biquadLP(float[] x, int sr, float fc, float q) {
  double w0 = 2 * Math.PI * fc / sr, al = Math.sin(w0) / (2 * q), cs = Math.cos(w0);
  double b0 = (1 - cs) / 2, b1 = 1 - cs, b2 = (1 - cs) / 2, a0 = 1 + al, a1 = -2 * cs, a2 = 1 - al;
  b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
  double x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (int i = 0; i < x.length; i++) {
    double x0 = x[i], y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x0; y2 = y1; y1 = y0;
    x[i] = (float) y0;
  }
}
