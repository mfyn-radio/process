// Globe-style glow: a tight and a wide halo around every lit dot, added on
// top of the finished frame. The cover gets no glow (its frame does).
// The same function makes the glow for the still frame and for every video
// frame, so preview, stills and video always match.

float GLOW_TIGHT = 6, GLOW_WIDE = 24, GLOW_GAIN = 0.42;
final int GLOW_REACH = 72;     // how far the glow spreads (3 x the wide radius)

// Glow rows y0..y1 of `flat` (the frame without glow) into `out`.
// noGlow marks where the glow is switched off (the cover).
void applyGlow(Canvas flat, float[] noGlow, Canvas out, int y0, int y1) {
  int w = flat.w;
  y0 = max(0, y0); y1 = min(flat.h, y1);
  // read a wider band than we write, so the edges come out the same as a full-frame pass
  int c0 = max(0, (y0 - 2 * GLOW_REACH) / 4 * 4);
  int c1 = min(flat.h, y1 + 2 * GLOW_REACH);
  int h = c1 - c0;
  float floor = OFF[0] / 255.0 * 1.05;
  float[] lum = new float[w * h];
  for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
    int gi = (c0 + y) * w + x, li = y * w + x;
    float v = (flat.r[gi] + flat.g[gi] + flat.b[gi]) / 765.0 - floor;
    lum[li] = v > 0 ? v * (1 - noGlow[gi]) : 0;
  }
  float[] tight = lum.clone();
  blurClamp(tight, w, h, GLOW_TIGHT);
  float[] wide = blurQuarter(lum, w, h, GLOW_WIDE);
  for (int y = y0; y < y1; y++) for (int x = 0; x < w; x++) {
    int gi = y * w + x, li = (y - c0) * w + x;
    float g = (0.9 * tight[li] + 2.2 * wide[li]) * GLOW_GAIN * (1 - noGlow[gi]);
    g = constrain(g, 0, 1);
    out.r[gi] = flat.r[gi] + (255 - flat.r[gi]) * g;
    out.g[gi] = flat.g[gi] + (255 - flat.g[gi]) * g;
    out.b[gi] = flat.b[gi] + (255 - flat.b[gi]) * g;
  }
}

// gaussian blur, edges clamped
void blurClamp(float[] a, int w, int h, float sigma) {
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
      for (int j = -rad; j <= rad; j++) s += a[o + min(w - 1, max(0, x + j))] * k[j + rad];
      tmp[x] = s;
    }
    System.arraycopy(tmp, 0, a, o, w);
  }
  for (int x = 0; x < w; x++) {
    for (int y = 0; y < h; y++) {
      float s = 0;
      for (int j = -rad; j <= rad; j++) s += a[min(h - 1, max(0, y + j)) * w + x] * k[j + rad];
      tmp[y] = s;
    }
    for (int y = 0; y < h; y++) a[y * w + x] = tmp[y];
  }
}

// wide blur done at quarter size (it's smooth anyway), then scaled back up
float[] blurQuarter(float[] a, int w, int h, float sigma) {
  int qw = (w + 3) / 4, qh = (h + 3) / 4;
  float[] q = new float[qw * qh];
  for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) q[(y / 4) * qw + x / 4] += a[y * w + x] / 16;
  blurClamp(q, qw, qh, sigma / 4);
  float[] out = new float[w * h];
  for (int y = 0; y < h; y++) {
    float fy = constrain((y - 1.5) / 4, 0, qh - 1);
    int y0 = (int) fy, y1 = min(qh - 1, y0 + 1);
    float ty = fy - y0;
    for (int x = 0; x < w; x++) {
      float fx = constrain((x - 1.5) / 4, 0, qw - 1);
      int x0 = (int) fx, x1 = min(qw - 1, x0 + 1);
      float tx = fx - x0;
      float top = q[y0 * qw + x0] * (1 - tx) + q[y0 * qw + x1] * tx;
      float bot = q[y1 * qw + x0] * (1 - tx) + q[y1 * qw + x1] * tx;
      out[y * w + x] = top * (1 - ty) + bot * ty;
    }
  }
  return out;
}
