// MFYN archive cover
// ------------------------------------------------------------
// The cover for archived MFYN radio shows: MFYN in black ink on orange
// card, with the episode number, the date and RADIO ARCHIVE. Only the number
// and the date change from episode to episode.
//
// List episodes in  input/episodes.csv , one per line:  2,8 October 2026
// Press Run. Every episode without a cover in  output/  yet is rendered as
// output/MFYN_archive_02.png, then the sketch closes itself.
//
// From the command line, one cover:  number=2 date="8 October 2026"
// (also input=<folder> output=<folder> size=<px>).
//
// The look is defined in Spec.pde. It is independent of the Reel and Album
// sketches on purpose: this cover is the brand anchor and should not drift.
// ------------------------------------------------------------

// ---------- settings ----------
int     SIZE    = 1080;              // 1080 to post, 2160 for print
int     SEED    = 7;                 // fixed, so every episode prints on the same paper
String  LABEL   = "RADIO ARCHIVE";
boolean PREVIEW = true;              // show each cover in the window when it's done
String  INPUT_DIR  = "input";
String  OUTPUT_DIR = "output";

class Episode { int number; String date; Episode(int n, String d) { number = n; date = d; } }

ArrayList<Episode> queue = new ArrayList<Episode>();
String argNumber = null, argDate = null;
PImage lastCover;
String status = "";

void settings() {
  size(540, 540);                    // preview window is half size
}

void setup() {
  readArgs();
  if (SIZE % B != 0) { println("MFYN: SIZE must be a multiple of 1080, using 1080"); SIZE = B; }
  loadFonts();
  new File(sketchPath(OUTPUT_DIR)).mkdirs();
  if (argNumber != null || argDate != null) {
    if (argNumber == null || argDate == null || !argNumber.trim().matches("\\d+")) {
      println("MFYN: give both number=<n> and date=\"<day month year>\"");
    } else {
      queue.add(new Episode(Integer.parseInt(argNumber.trim()), argDate.trim()));
    }
  } else {
    readEpisodes(new File(sketchPath(INPUT_DIR), "episodes.csv"));
  }
  for (int i = queue.size() - 1; i >= 0; i--) {
    if (outputFor(queue.get(i)).exists()) queue.remove(i);
  }
  println("MFYN: " + queue.size() + " cover(s) to render");
  background(20);
}

void draw() {
  if (lastCover != null && PREVIEW) image(lastCover, 0, 0, width, height);
  drawStatus();
  if (queue.isEmpty()) { println("MFYN: done"); exit(); return; }
  Episode ep = queue.remove(0);
  File out = outputFor(ep);
  status = "rendering " + out.getName() + " (" + queue.size() + " left)";
  PImage cover = render(ep.number, ep.date);
  cover.save(out.getAbsolutePath());
  println("MFYN: wrote " + out.getName());
  lastCover = cover;
}

// one line per episode: number,date. Blank lines and lines starting with # are skipped.
void readEpisodes(File csv) {
  if (!csv.exists()) { println("MFYN: no " + csv.getPath() + ", nothing to render"); return; }
  for (String line : loadStrings(csv.getAbsolutePath())) {
    line = line.trim();
    if (line.length() == 0 || line.startsWith("#")) continue;
    int comma = line.indexOf(',');
    String n = comma < 0 ? "" : line.substring(0, comma).trim();
    if (!n.matches("\\d+")) { println("MFYN: skipping line \"" + line + "\" (expected number,date)"); continue; }
    queue.add(new Episode(Integer.parseInt(n), line.substring(comma + 1).trim()));
  }
}

File outputFor(Episode ep) {
  String name = "MFYN_archive_" + nf(ep.number, 2) + (SIZE == B ? "" : "_" + SIZE) + ".png";
  return new File(sketchPath(OUTPUT_DIR), name);
}

// The whole cover: paper, then the wordmark in ink, then the small text in ink.
PImage render(int number, String date) {
  int S = SIZE;
  java.util.Random rng = new java.util.Random(SEED);
  float[][] img = makePaper(rng, S);

  Line[] big = { new Line(WORDMARK, wordmarkFont, WORDMARK_SIZE, WORDMARK_TRACK, WORDMARK_X, WORDMARK_BASELINE) };
  applyInk(rng, img, textMask(big, S, WORDMARK_BASELINE - WORDMARK_SIZE, WORDMARK_BASELINE + WORDMARK_SIZE * 0.3), S);

  String label = LABEL.toUpperCase();
  float labelX = B - MARGIN - trackedWidth(label, smallFont, SMALL_SIZE, SMALL_TRACK);
  Line[] small = {
    new Line("NO. " + nf(number, 2), smallFont, SMALL_SIZE, SMALL_TRACK, MARGIN, LINE1_BASELINE),
    new Line(date.toUpperCase(), smallFont, SMALL_SIZE, SMALL_TRACK, MARGIN, LINE2_BASELINE),
    new Line(label, smallFont, SMALL_SIZE, SMALL_TRACK, labelX, LINE2_BASELINE),
  };
  applyInk(rng, img, textMask(small, S, LINE1_BASELINE - SMALL_SIZE * 1.5, LINE2_BASELINE + SMALL_SIZE * 0.6), S);

  PImage out = createImage(S, S, RGB);
  out.loadPixels();
  for (int i = 0; i < out.pixels.length; i++) {
    int r = (int) constrain(img[0][i], 0, 255), g = (int) constrain(img[1][i], 0, 255), b = (int) constrain(img[2][i], 0, 255);
    out.pixels[i] = 0xFF000000 | (r << 16) | (g << 8) | b;
  }
  out.updatePixels();
  return out;
}

// command-line overrides: number=<n> date=<text> input=<folder> output=<folder> size=<px>
void readArgs() {
  if (args == null) return;
  for (String a : args) {
    int eq = a.indexOf('=');
    if (eq < 0) continue;
    String key = a.substring(0, eq), value = a.substring(eq + 1);
    if (key.equals("number")) argNumber = value;
    else if (key.equals("date")) argDate = value;
    else if (key.equals("input")) INPUT_DIR = value;
    else if (key.equals("output")) OUTPUT_DIR = value;
    else if (key.equals("size")) SIZE = int(value);
  }
}

void drawStatus() {
  noStroke();
  fill(0, 180);
  rect(0, height - 28, width, 28);
  fill(255);
  textSize(13);
  text(status, 8, height - 9);
}
