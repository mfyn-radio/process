// The paper colour. With RANDOM_COLOUR on, each episode gets its own colour,
// picked from its number, so a cover always comes out in the same colour when
// it's remade. The hues step round the colour wheel by the golden angle
// (137.5 degrees) from a random start, so they look random but neighbouring
// episodes are never alike. Every colour has the same lightness as the original orange
// (in the OKLab colour space), so the black ink reads equally well on all of
// them, and as much of the orange's colour strength as that hue allows.

float[] paperColour(int number) {
  if (!RANDOM_COLOUR) return PAPER;
  float start = (mix(COLOUR_SEED) >>> 40) / (float) (1L << 24) * TWO_PI;
  float hue = (start + number * radians(137.50776)) % TWO_PI;
  float[] lab = srgbToOklab(PAPER);
  float L = lab[0], C = sqrt(lab[1] * lab[1] + lab[2] * lab[2]);
  for (; C > 0; C -= 0.002) {
    float[] rgb = oklabToSrgb(L, C * cos(hue), C * sin(hue));
    if (rgb != null) return rgb;
  }
  return oklabToSrgb(L, 0, 0);
}

// SplitMix64, for the random starting hue.
long mix(long z) {
  z += 0x9E3779B97F4A7C15L;
  z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
  z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
  return z ^ (z >>> 31);
}

String hex(float[] c) {
  return String.format("#%02X%02X%02X", round(c[0]), round(c[1]), round(c[2]));
}

float toLinear(float v) { v /= 255; return v <= 0.04045 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4); }
float toSrgb(float v)   { return 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * pow(v, 1 / 2.4) - 0.055); }

float[] srgbToOklab(float[] c) {
  float r = toLinear(c[0]), g = toLinear(c[1]), b = toLinear(c[2]);
  float l = pow(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b, 1 / 3.0);
  float m = pow(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b, 1 / 3.0);
  float s = pow(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b, 1 / 3.0);
  return new float[] {
    0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s };
}

// null when the colour is outside sRGB
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
