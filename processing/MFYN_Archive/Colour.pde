// The paper colour. With RANDOM_COLOUR on, every cover gets a new random,
// muted colour: any hue, with lightness and colour strength picked at random
// within the ranges in Spec.pde. A colour is only used if the black ink still
// reads well on it, measured at the paper's darkest corner; otherwise another
// one is picked. The paper texture and the type are the same on every cover.

float[] paperColour() {
  if (!RANDOM_COLOUR) return PAPER;
  java.util.Random rng = new java.util.Random();     // a new colour every time
  for (int tries = 0; tries < 10000; tries++) {
    float L = PAPER_L_MIN + rng.nextFloat() * (PAPER_L_MAX - PAPER_L_MIN);
    float C = PAPER_C_MIN + rng.nextFloat() * (PAPER_C_MAX - PAPER_C_MIN);
    float h = rng.nextFloat() * TWO_PI;
    float[] rgb = oklabToSrgb(L, C * cos(h), C * sin(h));
    if (rgb == null) continue;                         // outside what a screen can show
    float[] corner = { rgb[0] * DARKEST_CORNER, rgb[1] * DARKEST_CORNER, rgb[2] * DARKEST_CORNER };
    if (contrast(corner, INK) >= MIN_CONTRAST) return rgb;
  }
  return PAPER;
}

// WCAG contrast ratio between two colours (1 to 21)
float contrast(float[] a, float[] b) {
  float la = luminance(a), lb = luminance(b);
  return (max(la, lb) + 0.05) / (min(la, lb) + 0.05);
}

float luminance(float[] c) {
  return 0.2126 * toLinear(c[0]) + 0.7152 * toLinear(c[1]) + 0.0722 * toLinear(c[2]);
}

String hex(float[] c) {
  return String.format("#%02X%02X%02X", round(c[0]), round(c[1]), round(c[2]));
}

float toLinear(float v) { v /= 255; return v <= 0.04045 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4); }
float toSrgb(float v)   { return 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * pow(v, 1 / 2.4) - 0.055); }

// OKLab to sRGB (0..255), or null when the colour is outside sRGB
float[] oklabToSrgb(float L, float a, float b) {
  float l = pow(L + 0.3963377774 * a + 0.2158037573 * b, 3);
  float m = pow(L - 0.1055613458 * a - 0.0638541728 * b, 3);
  float s = pow(L - 0.0894841775 * a - 1.2914855480 * b, 3);
  float[] lin = {
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s };
  float[] out = new float[3];
  for (int i = 0; i < 3; i++) {
    if (lin[i] < -1e-4 || lin[i] > 1 + 1e-4) return null;
    out[i] = toSrgb(constrain(lin[i], 0, 1));
  }
  return out;
}
