// MFYN Album Story generator
// ------------------------------------------------------------
// One folder per album inside  input/  (the tracks, tagged; cover
// embedded or as cover.jpg). Optionally a  featured.txt  in the folder
// with the featured track's number or part of its title.
//
// Press Run. Every album that doesn't have a video in  output/  yet is
// rendered as a 1080x1920 Instagram Story: the media player with the
// cover, album info and tracklist, over the rotating dot-matrix globe
// that pulses to the featured track. A still PNG is saved next to it.
//
// Needs ffmpeg + ffprobe installed (brew install ffmpeg).
// ------------------------------------------------------------

// ---------- settings ----------
float CLIP_SECONDS   = 15;      // story length (max 60)
float START_OVERRIDE = -1;      // -1 = auto-pick the loudest stretch, otherwise seconds into the featured track
int   FPS            = 30;
boolean PREVIEW      = true;    // draw frames in the window while rendering (slightly slower)
boolean SAVE_STILL   = true;    // also save a PNG of the first frame
String  INPUT_DIR    = "input";
String  OUTPUT_DIR   = "output";
// If Processing can't find ffmpeg, put the full path here, e.g. "/opt/homebrew/bin/ffmpeg"
String FFMPEG  = "";
String FFPROBE = "";

final int W = 1080, H = 1920;

ArrayList<File> queue = new ArrayList<File>();
Album job;            // the album currently rendering
Encoder enc;
int frameIdx = 0, frameCount_ = 0;

void settings() {
  size(W / 2, H / 2);           // preview window is half size
}

void setup() {
  frameRate(1000);
  findTools();
  loadSkinFonts();
  File in = new File(sketchPath(INPUT_DIR));
  in.mkdirs();
  new File(sketchPath(OUTPUT_DIR)).mkdirs();
  File[] dirs = in.listFiles();
  if (dirs != null) {
    java.util.Arrays.sort(dirs);
    for (File d : dirs) {
      if (!d.isDirectory()) continue;
      if (audioFiles(d).length == 0) continue;
      if (outputFor(d).exists()) continue;
      queue.add(d);
    }
  }
  println("MFYN: " + queue.size() + " album(s) to render");
}

void draw() {
  if (job == null) {
    if (queue.isEmpty()) { println("MFYN: done"); exit(); return; }
    startJob(queue.remove(0));
    return;
  }
  long t0 = millis();
  while (frameIdx < frameCount_ && millis() - t0 < 200) {
    int[] px = job.renderFrame(frameIdx);
    enc.write(px);
    if (frameIdx == 0 && SAVE_STILL) saveStill(px, stillFor(job.folder));
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

void startJob(File folder) {
  println("MFYN: " + folder.getName());
  job = new Album(folder);
  frameIdx = 0;
  frameCount_ = round(job.dur * FPS);
  enc = new Encoder(outputFor(folder), job.featured.file, job.start, job.dur);
}

File[] audioFiles(File dir) {
  File[] all = dir.listFiles();
  ArrayList<File> out = new ArrayList<File>();
  if (all != null) for (File f : all) {
    String n = f.getName().toLowerCase();
    if (n.endsWith(".flac") || n.endsWith(".mp3") || n.endsWith(".wav") || n.endsWith(".m4a") || n.endsWith(".aiff") || n.endsWith(".ogg")) out.add(f);
  }
  return out.toArray(new File[0]);
}

File outputFor(File folder) { return new File(sketchPath(OUTPUT_DIR), folder.getName() + "_story.mp4"); }
File stillFor(File folder)  { return new File(sketchPath(OUTPUT_DIR), folder.getName() + "_story.png"); }

void saveStill(int[] px, File f) {
  PImage img = createImage(W, H, RGB);
  img.loadPixels();
  arrayCopy(px, img.pixels);
  img.updatePixels();
  img.save(f.getAbsolutePath());
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
  text(job.artist + " - " + job.album + "   " + frameIdx + "/" + frameCount_ + "   (" + queue.size() + " left)", 8, height - 9);
}
