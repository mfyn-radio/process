// The orange dot-matrix player: layout and the parts that move.

// ---------- palette ----------
float[] BG    = { 13, 5, 3 };
float[] GRID  = { 30, 9, 4 };
float[] OR    = { 255, 92, 28 };     // lit orange
float[] LT    = { 255, 200, 176 };   // pale lit (title, ON AIR)
float[] DIM   = { 104, 34, 12 };
float[] FAINT = { 70, 22, 8 };       // unlit outlines
float[] NOTE_MID = { 140, 46, 16 };

// ---------- layout ----------
final int T1 = 250;                  // top of the header panel
final int T2 = 615;                  // top of the now-playing panel
final int B2 = 1575;                 // bottom of the now-playing panel
final int TEXT_X = 138, TEXT_MAXW = 712;
final int COVER_S = 340;
final int COVER_CX = 495, COVER_CY = T2 + 316;
final int PROGRESS_Y = T2 + 874;
final int[] ONAIR_DOT = { 532, T1 + 99 };

float[][] NOTE = { {0,0,1,1,1}, {0,0,1,0,1}, {0,0,1,0,0}, {0,0,1,0,0}, {1,1,1,0,0}, {1,1,1,0,0} };
float[][] POWER = { {0,0,0,1,0,0,0}, {0,1,0,1,0,1,0}, {1,0,0,1,0,0,1}, {1,0,0,0,0,0,1},
                    {1,0,0,0,0,0,1}, {0,1,0,0,0,1,0}, {0,0,1,1,1,0,0} };


// background: dark panel with a faint dot grid everywhere
void drawBackground(Canvas cv) {
  cv.fill(BG);
  Mask s = sprite(6, 0.30);
  for (int y = 0; y < cv.h; y++) for (int x = 0; x < cv.w; x++) {
    float a = s.v[(y % 6) * 6 + (x % 6)];
    if (a <= 0) continue;
    int i = y * cv.w + x;
    cv.r[i] += (GRID[0] - cv.r[i]) * a; cv.g[i] += (GRID[1] - cv.g[i]) * a; cv.b[i] += (GRID[2] - cv.b[i]) * a;
  }
}

// rounded rectangle outline made of dots
void dottedRect(Canvas cv, float x0, float y0, float x1, float y1, float r, float step, float dr, float[] col, float glow) {
  ArrayList<float[]> pts = new ArrayList<float[]>();
  dottedSeg(pts, x0 + r, y0, x1 - r, y0, step); dottedArc(pts, x1 - r, y0 + r, r, -90, 0, step);
  dottedSeg(pts, x1, y0 + r, x1, y1 - r, step); dottedArc(pts, x1 - r, y1 - r, r, 0, 90, step);
  dottedSeg(pts, x1 - r, y1, x0 + r, y1, step); dottedArc(pts, x0 + r, y1 - r, r, 90, 180, step);
  dottedSeg(pts, x0, y1 - r, x0, y0 + r, step); dottedArc(pts, x0 + r, y0 + r, r, 180, 270, step);
  int mw = (int) (x1 - x0) + 20, mh = (int) (y1 - y0) + 20, ss = 4;
  Mask m = new Mask(mw, mh);
  for (float[] p : pts) {
    float cx = p[0] - x0 + 10, cy = p[1] - y0 + 10;
    for (int y = max(0, floor(cy - dr - 1)); y <= min(mh - 1, ceil(cy + dr + 1)); y++)
      for (int x = max(0, floor(cx - dr - 1)); x <= min(mw - 1, ceil(cx + dr + 1)); x++) {
        int hit = 0;
        for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
          float dx = x + (sx + 0.5) / ss - cx, dy = y + (sy + 0.5) / ss - cy;
          if (dx * dx + dy * dy <= dr * dr) hit++;
        }
        m.v[y * mw + x] = max(m.v[y * mw + x], hit / float(ss * ss));
      }
  }
  if (glow > 0) cv.composite((int) x0 - 10, (int) y0 - 10, col, m.blur(4), glow);
  cv.composite((int) x0 - 10, (int) y0 - 10, col, m);
}

void dottedSeg(ArrayList<float[]> pts, float ax, float ay, float bx, float by, float step) {
  int n = max((int) (dist(ax, ay, bx, by) / step), 1);
  for (int i = 0; i < n; i++) { float t = i / float(n); pts.add(new float[] { ax + (bx - ax) * t, ay + (by - ay) * t }); }
}

void dottedArc(ArrayList<float[]> pts, float cx, float cy, float r, float a0, float a1, float step) {
  int n = max((int) (r * radians(abs(a1 - a0)) / step), 1);
  for (int i = 0; i < n; i++) {
    float a = radians(a0 + (a1 - a0) * i / n);
    pts.add(new float[] { cx + r * cos(a), cy + r * sin(a) });
  }
}

// solid block of dots with text punched out (the selected RADIO tab)
void filledDots(Canvas cv, int x0, int y0, int x1, int y1, int p, float[] col, float[][] hole) {
  int cols = (x1 - x0) / p, rows = (y1 - y0) / p;
  float[][] bm = new float[rows][cols];
  for (int j = 0; j < rows; j++) for (int i = 0; i < cols; i++) bm[j][i] = 1;
  bm[0][0] = 0; bm[0][cols - 1] = 0; bm[rows - 1][0] = 0; bm[rows - 1][cols - 1] = 0;
  int hc = (cols - cols(hole)) / 2, hr = (rows - hole.length) / 2;
  for (int j = 0; j < hole.length; j++) for (int i = 0; i < cols(hole); i++) bm[hr + j][hc + i] *= 1 - hole[j][i];
  dm(cv, x0, y0, bm, p, col, 0.4);
}

float[][] scale2(float[][] a) {
  float[][] o = new float[a.length * 2][a[0].length * 2];
  for (int j = 0; j < o.length; j++) for (int i = 0; i < o[0].length; i++) o[j][i] = a[j / 2][i / 2];
  return o;
}


// ---------- the static parts ----------
void drawHeader(Canvas cv) {
  dottedRect(cv, 118, T1, 872, T1 + 345, 12, 7, 2.4, DIM, 0.35);
  txt(cv, 138, T1 + 36, "MFYN", "F21", 6, OR);
  dottedRect(cv, 496, T1 + 34, 850, T1 + 164, 12, 7, 2.4, OR, 0.4);
  Mask d = disc(16);
  int dx = ONAIR_DOT[0] - d.w / 2, dy = ONAIR_DOT[1] - d.h / 2;
  cv.composite(dx, dy, LT, d);
  cv.composite(dx, dy, OR, d.blur(5), 0.4);
  txt(cv, 566, T1 + 57, "ON AIR", "F17", 5, LT);

  int ty0 = T1 + 190, ty1 = T1 + 310;
  filledDots(cv, 138, ty0, 352, ty1, 4, OR, bitmap("RADIO", "F15"));
  String[] labels = { "CD", "MP3" };
  int[][] boxes = { { 368, 542 }, { 558, 736 } };
  for (int k = 0; k < 2; k++) {
    dottedRect(cv, boxes[k][0], ty0, boxes[k][1], ty1, 10, 6.5, 1.9, FAINT, 0);
    float[][] b = bitmap(labels[k], "F15");
    dm(cv, (boxes[k][0] + boxes[k][1]) / 2.0 - cols(b) * 2, (ty0 + ty1) / 2.0 - b.length * 2, b, 4, DIM, 0.25);
  }
  dottedRect(cv, 752, ty0, 846, ty1, 10, 6.5, 1.9, FAINT, 0);
  dm(cv, 799 - 42, (ty0 + ty1) / 2.0 - 42, scale2(POWER), 6, OR, 0.5);
}

void drawNowPlaying(Canvas cv) {
  dottedRect(cv, 118, T2, 872, B2, 12, 7, 2.4, DIM, 0.35);
  int y = T2 + 22;
  txt(cv, 138, y, "NOW PLAYING", "F15", 4, DIM, 0.3);
  int[][] notes = { { 640, y + 4 }, { 722, y - 4 }, { 806, y + 4 } };
  for (int k = 0; k < 3; k++) dm(cv, notes[k][0], notes[k][1], NOTE, 8, k == 1 ? NOTE_MID : DIM, 0.3);
}

// Title and artist each get up to two lines. At the normal size there's room
// for three lines above the progress bar; when both need two, they drop to
// a smaller dot pitch with tighter spacing so all four fit.
void drawTitle(Canvas cv, String title, String artist) {
  int p = 6, gap = 98, artistGap = 104, y = T2 + 566;
  String[] lines = wrapTitle(title, "F13", p, TEXT_MAXW);
  String[] artistLines = wrapTitle(artist, "F13", p, TEXT_MAXW);
  if (lines.length + artistLines.length > 3) {
    p = 5; gap = 80; artistGap = 88; y = T2 + 540;
    lines = wrapTitle(title, "F13", p, TEXT_MAXW);
    artistLines = wrapTitle(artist, "F13", p, TEXT_MAXW);
  }
  for (String l : lines) { txt(cv, TEXT_X, y, l, "F13", p, LT); y += gap; }
  y += artistGap - gap;
  for (String l : artistLines) { txt(cv, TEXT_X, y, l, "F13", p, OR); y += gap; }
}


// ---------- the moving parts ----------
String clock(float t) { int s = (int) t; return (s / 60) + ":" + nf(s % 60, 2); }

void drawProgress(Canvas cv, float t, float total) {
  int y = PROGRESS_Y, x0 = TEXT_X, x1 = 850;
  int wa = txt(cv, x0, y, clock(t), "F15", 4, DIM, 0.3);
  float[][] bb = bitmap(clock(total), "F15");
  dm(cv, x1 - cols(bb) * 4, y, bb, 4, DIM, 0.3);
  int bx0 = x0 + wa + 18, bx1 = x1 - cols(bb) * 4 - 30;
  dottedRect(cv, bx0, y + 6, bx1, y + 46, 12, 6, 1.6, FAINT, 0);
  int p = 4;
  int n = (bx1 - bx0 - 20) / p;
  int lit = (int) (n * constrain(t / total, 0, 1));
  float[][] bar = new float[5][n];
  for (int j = 0; j < 5; j++) for (int i = 0; i < lit; i++) bar[j][i] = 1;
  dm(cv, bx0 + 10, y + 16, bar, p, OR, 0.45);
  float[][] head = { {1}, {1}, {1}, {1}, {1}, {1}, {1} };
  dm(cv, bx0 + 10 + lit * p, y + 12, head, p, LT, 0.5);
}

// ON AIR lamp breathes slowly
void drawOnAirPulse(Canvas cv, float t) {
  float k = 0.5 + 0.5 * cos(TWO_PI * t / 1.6);
  Mask d = disc(17);
  cv.composite(ONAIR_DOT[0] - d.w / 2, ONAIR_DOT[1] - d.h / 2, new float[] { 60, 16, 6 }, d, (1 - k) * 0.45);
  Mask g = disc(40).blur(10);
  cv.composite(ONAIR_DOT[0] - g.w / 2, ONAIR_DOT[1] - g.h / 2, OR, g, 0.25 * k);
}
