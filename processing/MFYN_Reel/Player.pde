// The white dot-matrix player: layout and the parts that move.

// ---------- brightness levels (greys) ----------
// The song title is the only element at full white.
float[] BG        = { 0, 0, 0 };
float[] OFF       = { 18, 18, 18 };      // unlit grid dots
float[] DIM       = { 64, 64, 64 };      // panel outlines, NOW PLAYING, notes, times, progress track
float[] MID       = { 125, 125, 125 };   // artist, scope, ON AIR frame, cover frame, progress fill
float[] BRIGHT    = { 179, 179, 179 };   // MFYN, ON AIR and its dot, progress head
float[] HIGHLIGHT = { 255, 255, 255 };   // song title

float DOT_R = 0.36;                      // text dot radius, as a fraction of the dot pitch

// ---------- layout (1080x1920, 6 px master dot grid) ----------
final int X0 = 118, X1 = 872;            // panel left / right
final int T1 = 250, B1 = 440;            // header panel (MFYN + ON AIR)
final int T2 = 460, B2 = 1556;           // main panel
final int TEXT_X = 138, TEXT_R = 852;
final int TEXT_MAXW = TEXT_R - TEXT_X;
final int COVER_S = 480;
final int COVER_CX = 495;
final int COVER_Y0 = T2 + 132;           // cover top
final int COVER_CY = COVER_Y0 + COVER_S / 2;
final int TITLE_Y = COVER_Y0 + COVER_S + 70;
float TITLE_P  = 6;                      // title dot pitch
String ARTIST_FONT = "F13";              // artist: same font as the title
float  ARTIST_P    = 4.8;                // 20% smaller than the title (6)
final int PROGRESS_Y = B2 - 85;          // top of the time labels
final int TEXT_BOTTOM = PROGRESS_Y - 16; // the artist stops above the progress row
final int[] ONAIR_DOT = { 532, T1 + 93 };

float[][] NOTE = { {0,0,1,1,1}, {0,0,1,0,1}, {0,0,1,0,0}, {0,0,1,0,0}, {1,1,1,0,0}, {1,1,1,0,0} };


// background: black with a faint dot grid everywhere
void drawBackground(Canvas cv) {
  cv.fill(BG);
  Mask s = sprite(6, 0.30);
  for (int y = 0; y < cv.h; y++) for (int x = 0; x < cv.w; x++) {
    float a = s.v[(y % 6) * 6 + (x % 6)];
    if (a <= 0) continue;
    int i = y * cv.w + x;
    cv.r[i] += (OFF[0] - cv.r[i]) * a; cv.g[i] += (OFF[1] - cv.g[i]) * a; cv.b[i] += (OFF[2] - cv.b[i]) * a;
  }
}

// rounded rectangle outline made of dots
void dottedRect(Canvas cv, float x0, float y0, float x1, float y1, float r, float step, float dr, float[] col) {
  ArrayList<float[]> pts = new ArrayList<float[]>();
  dottedSeg(pts, x0 + r, y0, x1 - r, y0, step); dottedArc(pts, x1 - r, y0 + r, r, -90, 0, step);
  dottedSeg(pts, x1, y0 + r, x1, y1 - r, step); dottedArc(pts, x1 - r, y1 - r, r, 0, 90, step);
  dottedSeg(pts, x1 - r, y1, x0 + r, y1, step); dottedArc(pts, x0 + r, y1 - r, r, 90, 180, step);
  dottedSeg(pts, x0, y1 - r, x0, y0 + r, step); dottedArc(pts, x0 + r, y0 + r, r, 180, 270, step);
  int mw = (int) (x1 - x0) + 20, mh = (int) (y1 - y0) + 20, ss = 6;
  Mask m = new Mask(mw, mh);
  for (float[] p : pts) {
    float cx = p[0] - x0 + 10, cy = p[1] - y0 + 10;
    for (int y = max(0, floor(cy - dr - 1)); y <= min(mh - 1, ceil(cy + dr + 1)); y++)
      for (int x = max(0, floor(cx - dr - 1)); x <= min(mw - 1, ceil(cx + dr + 1)); x++) {
        int hit = 0;
        for (int sy = 0; sy < ss; sy++) for (int sx = 0; sx < ss; sx++) {
          float dx = x + (sx + 0.5) / ss - cx, dy = y + (sy + 0.5) / ss - cy;
          if (dx * dx + dy * dy <= sq(dr + DOT_BIAS)) hit++;
        }
        m.v[y * mw + x] = max(m.v[y * mw + x], hit / float(ss * ss));
      }
  }
  cv.composite((int) x0 - 10, (int) y0 - 10, col, m);
}

void dottedSeg(ArrayList<float[]> pts, float ax, float ay, float bx, float by, float step) {
  int n = max(round(dist(ax, ay, bx, by) / step), 1);
  for (int i = 0; i < n; i++) { float t = i / float(n); pts.add(new float[] { ax + (bx - ax) * t, ay + (by - ay) * t }); }
}

void dottedArc(ArrayList<float[]> pts, float cx, float cy, float r, float a0, float a1, float step) {
  int n = max(round(r * radians(abs(a1 - a0)) / step), 1);
  for (int i = 0; i < n; i++) {
    float a = radians(a0 + (a1 - a0) * i / n);
    pts.add(new float[] { cx + r * cos(a), cy + r * sin(a) });
  }
}


// ---------- the static parts ----------
void drawHeader(Canvas cv) {
  dottedRect(cv, X0, T1, X1, B1, 12, 7, 2.4, DIM);
  txt(cv, TEXT_X, T1 + 30, "MFYN", "F21", 6, BRIGHT);
  dottedRect(cv, 496, T1 + 28, 850, T1 + 158, 12, 7, 2.4, MID);
  Mask d = disc(17.5);
  cv.composite(ONAIR_DOT[0] - d.w / 2, ONAIR_DOT[1] - d.h / 2, BRIGHT, d);
  txt(cv, 566, T1 + 51, "ON AIR", "F17", 5, BRIGHT);
}

void drawNowPlaying(Canvas cv) {
  dottedRect(cv, X0, T2, X1, B2, 12, 7, 2.4, DIM);
  int y = T2 + 22;
  txt(cv, TEXT_X, y, "NOW PLAYING", "F15", 4, DIM);
  int[][] notes = { { 640, y + 4 }, { 722, y - 4 }, { 806, y + 4 } };
  for (int k = 0; k < 3; k++) dm(cv, notes[k][0], notes[k][1], NOTE, 8, DIM);
}

// title in white (up to two lines), artist 20% smaller in MID just under it,
// wrapping onto as many lines as fit above the progress row
void drawTitle(Canvas cv, String title, String artist) {
  String[] lines = wrapTitle(title, "F13", TITLE_P, TEXT_MAXW);
  int y = TITLE_Y;
  for (String l : lines) { txtFine(cv, TEXT_X, y, l, "F13", TITLE_P, HIGHLIGHT); y += round(98 * TITLE_P / 6); }
  y += 6;
  int h = ceil(FONTS.get(ARTIST_FONT).height * ARTIST_P);
  int gap = round(h * 98 / 78.0);         // same line spacing, relative to height, as the title
  int fit = max(1, (TEXT_BOTTOM - y - h) / gap + 1);
  for (String l : wrapLines(artist.toUpperCase(), ARTIST_FONT, ARTIST_P, TEXT_MAXW, fit)) {
    txtFine(cv, TEXT_X, y, l, ARTIST_FONT, ARTIST_P, MID);
    y += gap;
  }
}


// ---------- the moving parts ----------
String clock(float t) { int s = (int) t; return (s / 60) + ":" + nf(s % 60, 2); }

void drawProgress(Canvas cv, float t, float total) {
  int ly = PROGRESS_Y;
  txt(cv, TEXT_X, ly, clock(t), "F15", 4, DIM);
  String end = clock(total);
  txt(cv, TEXT_R - advWidth(end, "F15") * 4, ly, end, "F15", 4, DIM);
  int tx0 = 235, tx1 = 754, ty0 = ly + 8;
  dottedRect(cv, tx0, ty0, tx1, ty0 + 40, 14, 7, 2.2, DIM);
  // fill: 3 px dots, 8 rows; head: one brighter column at the fill edge
  int fx0 = tx0 + 11, fx1 = tx1 - 12;
  float fillX = fx0 + (fx1 - fx0) * constrain(t / total, 0, 1);
  int n = max(0, ceil((fillX - 2 - fx0) / 3));
  float[][] bar = new float[8][max(n, 1)];
  for (int j = 0; j < 8; j++) for (int i = 0; i < n; i++) bar[j][i] = 1;
  if (n > 0) dm(cv, fx0, ty0 + 8, bar, 3, MID, 0, 0.4833);
  float[][] head = new float[8][1];
  for (int j = 0; j < 8; j++) head[j][0] = 1;
  dm(cv, round(fillX - 1), ty0 + 8, head, 3, BRIGHT, 0, 0.4833);
}

// ON AIR lamp breathes slowly
void drawOnAirPulse(Canvas cv, float t) {
  float k = 0.5 + 0.5 * cos(TWO_PI * t / 1.6);
  Mask d = disc(18.5);
  cv.composite(ONAIR_DOT[0] - d.w / 2, ONAIR_DOT[1] - d.h / 2, BG, d, (1 - k) * 0.45);
}
