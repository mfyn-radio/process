// The rotating dot-matrix globe behind the player.
// Latitude / longitude lines are lit on a 6px dot grid (same pitch as the
// orange player), unlit dots stay faintly visible, and the lines glow and
// pulse with the low end of the featured track.

float GLOBE_CX = 540, GLOBE_CY = 880, GLOBE_R = 800;   // top and bottom inside the frame, sides run off
float GLOBE_TILT = 18;          // degrees, top tipped toward the viewer
float GRID_STEP = 15;           // degrees between grid lines
float DEG_PER_SECOND = 6;       // one turn a minute
float LINE_BRIGHTNESS = 0.72;
float UNLIT = 0.07;             // brightness of unlit dots
float LINE_WIDTH = 0.95;        // in dots
float PULSE_LOWPASS_HZ = 180;   // what drives the glow
float OCC_STRENGTH = 0.75;      // how much light the player blocks around itself
float WRAP_STRENGTH = 3.0;      // globe light spilling onto the player's edges
final int DP = 6;               // dot pitch
final float DOT_R = 0.36;       // dot radius, fraction of the pitch

class Globe {
  int gw = W / DP, gh = H / DP;
  float[] lat, lon0, gLat, gLon, disc, shade, latLines, poleFade;
  float[] spr = new float[DP * DP];
  float sprMean;
  float[] G, G1, G2;

  Globe() {
    int n = gw * gh;
    lat = new float[n]; lon0 = new float[n]; disc = new float[n]; shade = new float[n];
    float ct = cos(radians(GLOBE_TILT)), st = sin(radians(GLOBE_TILT));
    for (int j = 0; j < gh; j++) for (int i = 0; i < gw; i++) {
      float x = (i + 0.5) * DP, y = (j + 0.5) * DP;
      float u = (x - GLOBE_CX) / GLOBE_R, v = (y - GLOBE_CY) / GLOBE_R;
      float r2 = u * u + v * v;
      float z = sqrt(constrain(1 - r2, 0, 1));
      float y1 = v * ct - z * st, z1 = v * st + z * ct;
      int k = j * gw + i;
      lat[k] = degrees(asin(constrain(-y1, -1, 1)));
      lon0[k] = degrees(atan2(u, z1));
      disc[k] = constrain((GLOBE_R - sqrt(r2) * GLOBE_R) / DP + 0.5, 0, 1);
      shade[k] = 0.35 + 0.65 * pow(z, 0.6);
    }
    gLat = gradMag(lat, false);
    gLon = gradMag(lon0, true);
    latLines = new float[n]; poleFade = new float[n];
    for (int k = 0; k < n; k++) {
      latLines[k] = abs(lat[k]) < 82 ? line(lat[k], gLat[k]) : 0;
      poleFade[k] = constrain((76 - abs(lat[k])) / 10, 0, 1);   // meridians stop short of the pole
    }
    // one round dot, supersampled
    int ss = 8; float sum = 0;
    for (int y = 0; y < DP; y++) for (int x = 0; x < DP; x++) {
      int hit = 0;
      for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
        float px = x + (sx + 0.5) / ss - DP / 2.0, py = y + (sy + 0.5) / ss - DP / 2.0;
        if (px * px + py * py <= sq(DP * DOT_R)) hit++;
      }
      spr[y * DP + x] = hit / (float) (ss * ss);
      sum += spr[y * DP + x];
    }
    sprMean = sum / (DP * DP);
    G = new float[n]; G1 = new float[n]; G2 = new float[n];
  }

  // degrees per dot, like numpy.gradient (wrap-aware for longitude)
  float[] gradMag(float[] a, boolean wrap) {
    float[] out = new float[a.length];
    for (int j = 0; j < gh; j++) for (int i = 0; i < gw; i++) {
      int il = max(0, i - 1), ir = min(gw - 1, i + 1), jt = max(0, j - 1), jb = min(gh - 1, j + 1);
      float dx = diff(a[j * gw + ir], a[j * gw + il], wrap) / max(1, ir - il);
      float dy = diff(a[jb * gw + i], a[jt * gw + i], wrap) / max(1, jb - jt);
      out[j * gw + i] = sqrt(dx * dx + dy * dy) + 1e-6;
    }
    return out;
  }
  float diff(float a, float b, boolean wrap) {
    float d = a - b;
    if (wrap) { while (d > 180) d -= 360; while (d < -180) d += 360; }
    return d;
  }

  // coverage of the nearest grid line at this value
  float line(float val, float g) {
    float f = val / GRID_STEP + 0.5;
    f = abs((f - floor(f)) - 0.5) * GRID_STEP;
    return constrain(LINE_WIDTH / 2 + 0.5 - f / g, 0, 1);
  }

  // fills bg (W x H, 0..255) with the globe at time t and pulse p (0..1)
  void render(float[] bg, float t, float p) {
    int n = gw * gh;
    for (int k = 0; k < n; k++) {
      float lon = lon0[k] + t * DEG_PER_SECOND;
      float v = max(latLines[k], line(lon, gLon[k]) * poleFade[k]) * shade[k] * disc[k];
      G[k] = pow(constrain(v * 1.25, 0, 1), 0.8) * LINE_BRIGHTNESS;
    }
    // glow: a tight and a wide halo around the lit dots
    arrayCopy(G, G1); arrayCopy(G, G2);
    gaussian(G1, gw, gh, 1.0);
    blurBox3(G2, gw, gh, 4.0);
    float gk = sprMean * (0.45 + 1.4 * p);
    for (int k = 0; k < n; k++) G1[k] = (0.9 * G1[k] + 2.2 * G2[k]) * gk;

    float lit = 0.8 + 0.2 * p;
    for (int y = 0; y < H; y++) {
      int j = min(y / DP, gh - 1), sy = y % DP;
      float fy = constrain((y + 0.5) / DP - 0.5, 0, gh - 1);
      int j0 = (int) fy, j1 = min(j0 + 1, gh - 1);
      float ty = fy - j0;
      for (int x = 0; x < W; x++) {
        int i = min(x / DP, gw - 1);
        int k = j * gw + i;
        float s = spr[sy * DP + x % DP];
        float dot = max(G[k] * s * lit, UNLIT * disc[k] * s);
        float fx = constrain((x + 0.5) / DP - 0.5, 0, gw - 1);
        int i0 = (int) fx, i1 = min(i0 + 1, gw - 1);
        float tx = fx - i0;
        float glow = (G1[j0 * gw + i0] * (1 - tx) + G1[j0 * gw + i1] * tx) * (1 - ty) + (G1[j1 * gw + i0] * (1 - tx) + G1[j1 * gw + i1] * tx) * ty;
        bg[y * W + x] = min(1, dot + glow) * 255;
      }
    }
  }
}
