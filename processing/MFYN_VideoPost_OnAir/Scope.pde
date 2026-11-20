// Audio-reactive oscilloscope line, drawn in dots behind the cover.
// Only the low end of the track drives it (smooth, rounded waves), each
// frame is blended with the previous few, and big swings are softly limited.

float SCOPE_LOWPASS_HZ = 140;
float SCOPE_GAIN       = 2.6;
int   SCOPE_P          = 6;      // dot pitch, same as the background grid
int   SCOPE_ROWS       = 41;     // +-20 rows = +-120px

class Scope {
  float[] aud;          // mono samples, low-passed
  int sr;
  float t0, peak;
  int cols, win, sy0;
  float[] taper;

  Scope(float[] samples, int sr, float t0) {
    this.sr = sr; this.t0 = t0;
    aud = lowpass(samples, sr, SCOPE_LOWPASS_HZ);
    peak = percentileAbs(aud, 99.5);
    if (peak <= 0) peak = 1;
    cols = W / SCOPE_P;                                // wave spans the full frame width
    win = (int) (sr * 0.100 * (cols / 119.0));         // ~170ms of audio across the frame
    sy0 = (COVER_CY / SCOPE_P - SCOPE_ROWS / 2) * SCOPE_P;
    taper = new float[cols];
    for (int i = 0; i < cols; i++) taper[i] = pow(sin(PI * i / (cols - 1)), 0.6);
  }

  float[] wave(float t) {
    int end = (int) ((t - t0) * sr);
    int per = win / cols;
    float[] v = new float[cols];
    for (int c = 0; c < cols; c++) {
      float s = 0;
      for (int k = 0; k < per; k++) {
        int i = end - win + c * per + k;
        if (i >= 0 && i < aud.length) s += aud[i];
      }
      v[c] = s / per / peak;
    }
    return v;
  }

  float[][] bitmap(float t) {
    float[] w = { 1.0, 0.6, 0.35, 0.2 };
    float ws = 0;
    float[] v = new float[cols];
    for (int j = 0; j < w.length; j++) {
      float[] a = wave(t - j / (float) FPS);
      for (int c = 0; c < cols; c++) v[c] += w[j] * a[c];
      ws += w[j];
    }
    int half = SCOPE_ROWS / 2;
    float[][] bm = new float[SCOPE_ROWS][cols];
    int prev = -1;
    for (int c = 0; c < cols; c++) {
      float x = (float) Math.tanh(v[c] / ws * SCOPE_GAIN) * taper[c];
      int row = constrain(round(half - x * half), 0, SCOPE_ROWS - 1);
      if (prev < 0) prev = row;
      for (int r = min(prev, row); r <= max(prev, row); r++) bm[r][c] = 1;
      prev = row;
    }
    return bm;
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

float percentileAbs(float[] a, float pct) {
  float[] s = new float[a.length];
  for (int i = 0; i < a.length; i++) s[i] = abs(a[i]);
  java.util.Arrays.sort(s);
  return s[min(s.length - 1, (int) (s.length * pct / 100))];
}
