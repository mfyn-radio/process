// Uncoated orange cardstock: fine tooth, mid grain, slow mottling, fibres,
// then a soft light from the top left and a gentle corner vignette.
// Returns the paper as three float channels (r, g, b), 0..255.

float[][] makePaper(java.util.Random rng, int S) {
  int k = S / B;

  float[] fine = noise(rng, 0, 1, false);
  float[] mott = noise(rng, 0.5, 0.5, true);
  gaussian(mott, B, B, MOTTLE_BLUR);
  float mm = mean(mott);
  float[] mid = noise(rng, 0.5, 0.5, true);
  gaussian(mid, B, B, MID_BLUR);
  float mi = mean(mid);
  float[] tex = new float[B * B];
  for (int i = 0; i < tex.length; i++) {
    tex[i] = fine[i] * FINE_AMP + (mid[i] - mi) * MID_SCALE * MID_AMP + (mott[i] - mm) * MOTTLE_SCALE * MOTTLE_AMP;
  }
  tex = upscale(tex, S);

  // fibres: short faint strokes, drawn at full size, slightly blurred
  PGraphics fg = createGraphics(S, S);
  fg.noSmooth();
  fg.beginDraw();
  fg.background(0);
  fg.strokeWeight(k);
  for (int n = 0; n < FIBRES; n++) {
    float x = rng.nextInt(B) * k, y = rng.nextInt(B) * k;
    float len = (FIBRE_LEN_MIN + rng.nextInt(FIBRE_LEN_MAX - FIBRE_LEN_MIN)) * k;
    float a = rng.nextFloat() * PI;
    fg.stroke(FIBRE_LEVEL_MIN + rng.nextInt(FIBRE_LEVEL_MAX - FIBRE_LEVEL_MIN));
    fg.line(x, y, x + len * cos(a), y + len * sin(a));
  }
  fg.endDraw();
  fg.loadPixels();
  float[] fib = new float[S * S];
  for (int i = 0; i < fib.length; i++) fib[i] = (fg.pixels[i] & 255) / 255.0;
  gaussian(fib, S, S, FIBRE_BLUR * k);
  for (int i = 0; i < tex.length; i++) tex[i] += (fib[i] - FIBRE_OFFSET) * FIBRE_AMP * FIBRE_SIGN;

  float[][] img = new float[3][S * S];
  for (int y = 0; y < S; y++) {
    float yy = y / (float) S;
    for (int x = 0; x < S; x++) {
      float xx = x / (float) S;
      float light = LIGHT_BASE - LIGHT_FALL * (xx * LIGHT_X + yy * LIGHT_Y);
      float vign = 1 - VIGNETTE * ((xx - 0.5) * (xx - 0.5) + (yy - 0.5) * (yy - 0.5)) * 2;
      int i = y * S + x;
      for (int c = 0; c < 3; c++) img[c][i] = (PAPER[c] + tex[i]) * light * vign;
    }
  }
  return img;
}
