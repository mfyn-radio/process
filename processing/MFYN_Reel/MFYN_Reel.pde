// MFYN Reel generator
// ------------------------------------------------------------
// Drop audio files (FLAC / MP3 / WAV with tags) into  input/
// Press Run. Every track that doesn't have a video in  output/  yet
// is rendered as a 1080x1920 Instagram Reel with its audio, then the
// sketch closes itself when the queue is empty.
//
// Needs ffmpeg + ffprobe installed (brew install ffmpeg).
//
// The Make Reels automation (intake/reels.py) runs this from the command
// line with  input=<folder> output=<folder> seconds=<n>  to override the
// settings below.
// ------------------------------------------------------------

// ---------- settings ----------
float CLIP_SECONDS   = 30;      // reel length (max 60)
float START_OVERRIDE = -1;      // -1 = auto-pick the loudest stretch, otherwise seconds into the track
int   FPS            = 30;
boolean PREVIEW      = true;    // draw frames in the window while rendering (slightly slower)
String  INPUT_DIR    = "input";
String  OUTPUT_DIR   = "output";
// If Processing can't find ffmpeg, put the full path here, e.g. "/opt/homebrew/bin/ffmpeg"
String FFMPEG  = "";
String FFPROBE = "";

final int W = 1080, H = 1920;

ArrayList<File> queue = new ArrayList<File>();
Job job;              // the track currently rendering
Encoder enc;
int frameIdx = 0, frameCount_ = 0;

void settings() {
  size(W / 2, H / 2);           // preview window is half size
}

void setup() {
  frameRate(1000);
  readArgs();
  findTools();
  loadFonts();
  File in = new File(sketchPath(INPUT_DIR));
  in.mkdirs();
  new File(sketchPath(OUTPUT_DIR)).mkdirs();
  File[] files = in.listFiles();
  if (files != null) {
    java.util.Arrays.sort(files);
    for (File f : files) {
      String n = f.getName().toLowerCase();
      if (!(n.endsWith(".flac") || n.endsWith(".mp3") || n.endsWith(".wav") || n.endsWith(".m4a") || n.endsWith(".aiff") || n.endsWith(".ogg"))) continue;
      if (outputFor(f).exists()) continue;
      queue.add(f);
    }
  }
  println("MFYN: " + queue.size() + " track(s) to render");
}

void draw() {
  if (job == null) {
    if (queue.isEmpty()) { println("MFYN: done"); exit(); return; }
    startJob(queue.remove(0));
    return;
  }
  // render a few frames per draw() so the window stays responsive
  long t0 = millis();
  while (frameIdx < frameCount_ && millis() - t0 < 200) {
    int[] px = job.renderFrame(frameIdx);
    enc.write(px);
    if (PREVIEW && (frameIdx % 3 == 0 || frameIdx == frameCount_ - 1)) showPreview(px);
    frameIdx++;
  }
  drawStatus();
  if (frameIdx >= frameCount_) {
    enc.finish();
    println("MFYN: wrote " + enc.out.getName());
    job = null;
  }
}

void startJob(File f) {
  println("MFYN: " + f.getName());
  job = new Job(f);
  frameIdx = 0;
  frameCount_ = round(job.dur * FPS);
  enc = new Encoder(outputFor(f), f, job.start, job.dur);
}

// command-line overrides: input=<folder> output=<folder> seconds=<n>
void readArgs() {
  if (args == null) return;
  for (String a : args) {
    int eq = a.indexOf('=');
    if (eq < 0) continue;
    String key = a.substring(0, eq), value = a.substring(eq + 1);
    if (key.equals("input")) INPUT_DIR = value;
    else if (key.equals("output")) OUTPUT_DIR = value;
    else if (key.equals("seconds")) CLIP_SECONDS = float(value);
  }
}

File outputFor(File audio) {
  String base = audio.getName().replaceAll("\\.[^.]+$", "");
  return new File(sketchPath(OUTPUT_DIR), base + "_reel.mp4");
}

PImage previewImg;
void showPreview(int[] px) {
  if (previewImg == null) previewImg = createImage(W, H, RGB);
  previewImg.loadPixels();
  arrayCopy(px, previewImg.pixels);
  previewImg.updatePixels();
  image(previewImg, 0, 0, width, height);
}

void drawStatus() {
  noStroke();
  fill(0, 180);
  rect(0, height - 28, width, 28);
  fill(255);
  textSize(13);
  text(job.artist + " - " + job.title + "   " + frameIdx + "/" + frameCount_ + "   (" + queue.size() + " left)", 8, height - 9);
}
