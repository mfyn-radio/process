// One track: read its tags, cover and audio, pick where the clip starts,
// draw everything that doesn't move once, then render frames.

class Job {
  File file;
  String title = "", artist = "";
  float length, start, dur;
  Canvas base;          // finished static frame (with cover)
  Canvas baseNoCover;   // same frame without the cover, for the scope to pass behind
  float[] coverAlpha;   // where the cover sits (scope is hidden there)
  float[] boxAlpha;     // where the scope is allowed to show (inside the panel)
  Scope scope;
  Canvas work;
  int[] px;

  Job(File f) {
    file = f;
    readTags();
    if (title.length() == 0) title = f.getName().replaceAll("\\.[^.]+$", "");
    dur = min(CLIP_SECONDS, 60);
    dur = min(dur, length);

    // audio for picking the start (whole track, low rate)
    float[] low = decode(f, 0, length + 1, 2000);
    start = START_OVERRIDE >= 0 ? START_OVERRIDE : loudestStart(low, 2000);
    start = constrain(start, 0, max(0, length - dur));

    // audio for the scope (around the clip, full detail)
    int sr = 22050;
    float t0 = max(0, start - 1);
    scope = new Scope(decode(f, t0, dur + 2, sr), sr, t0);

    PImage cover = findCover(f);
    buildBase(cover);
    work = base.copy();
  }

  void readTags() {
    String json = run(FFPROBE, "-v", "error", "-show_entries", "format=duration:format_tags", "-of", "json", file.getAbsolutePath());
    JSONObject fmt = parseJSONObject(json).getJSONObject("format");
    length = parseFloat(fmt.getString("duration"));
    JSONObject tags = fmt.hasKey("tags") ? fmt.getJSONObject("tags") : new JSONObject();
    for (Object k : tags.keys()) {
      String key = ((String) k).toLowerCase();
      if (key.equals("title")) title = tags.getString((String) k);
      if (key.equals("artist")) artist = tags.getString((String) k);
      if (key.equals("album_artist") && artist.length() == 0) artist = tags.getString((String) k);
    }
  }

  // embedded artwork first, then cover.jpg / folder.jpg / <track name>.jpg next to the file
  PImage findCover(File f) {
    File tmp = new File(sketchPath("cover_tmp.png"));
    tmp.delete();
    run(FFMPEG, "-v", "error", "-y", "-i", f.getAbsolutePath(), "-an", "-frames:v", "1", tmp.getAbsolutePath());
    if (tmp.exists() && tmp.length() > 0) { PImage img = loadImage(tmp.getAbsolutePath()); tmp.delete(); if (img != null) return img; }
    String base = f.getName().replaceAll("\\.[^.]+$", "");
    String[] names = { base + ".jpg", base + ".png", "cover.jpg", "cover.png", "folder.jpg", "folder.png" };
    for (String n : names) {
      File c = new File(f.getParentFile(), n);
      if (c.exists()) { PImage img = loadImage(c.getAbsolutePath()); if (img != null) return img; }
    }
    println("MFYN: no cover found for " + f.getName() + ", using a blank one");
    PImage blank = createImage(8, 8, RGB);
    return blank;
  }

  // the loudest stretch of the track (after the intro, before the outro)
  float loudestStart(float[] x, int sr) {
    int secs = x.length / sr;
    float[] rms = new float[secs];
    for (int s = 0; s < secs; s++) {
      float a = 0;
      for (int i = s * sr; i < (s + 1) * sr; i++) a += x[i] * x[i];
      rms[s] = sqrt(a / sr);
    }
    int d = max(1, round(dur));
    int lo = min(30, max(0, secs - d)), hi = max(lo, secs - 30 - d);
    if (secs < 90) { lo = 0; hi = max(0, secs - d); }
    int best = lo; float bestV = -1;
    for (int s = lo; s <= hi; s++) {
      float v = 0;
      for (int k = s; k < min(secs, s + d); k++) v += rms[k];
      if (v > bestV) { bestV = v; best = s; }
    }
    return best;
  }

  void buildBase(PImage cover) {
    Canvas c = new Canvas(W, H);
    drawBackground(c);
    drawHeader(c);
    drawNowPlaying(c);
    drawTitle(c, title, artist.length() > 0 ? artist : "UNKNOWN ARTIST");
    // static grain, so the screen doesn't look perfectly clean
    float[] gr = new float[W * H];
    randomSeed(3);
    for (int i = 0; i < gr.length; i++) gr[i] = randomGaussian();
    gaussian(gr, W, H, 0.6);
    for (int i = 0; i < gr.length; i++) { float v = gr[i] * 3; c.r[i] += v; c.g[i] += v; c.b[i] += v; }

    baseNoCover = c.copy();
    Canvas art = treatCover(cover, COVER_S);
    drawCover(c, art);
    base = c;

    int S = COVER_S, pad = 24;
    coverAlpha = new float[W * H];
    Mask rr = roundRect(S + 2 * pad, S + 2 * pad, 30);
    int ax = COVER_CX - S / 2 - pad, ay = COVER_CY - S / 2 - pad;
    for (int y = 0; y < rr.h; y++) for (int x = 0; x < rr.w; x++) coverAlpha[(ay + y) * W + ax + x] = rr.v[y * rr.w + x];
    boxAlpha = new float[W * H];
    for (int y = T2 + 8; y < B2 - 8; y++) for (int x = 128; x < 862; x++) boxAlpha[y * W + x] = 1;
  }

  int[] renderFrame(int i) {
    float t = start + i / (float) FPS;
    // only these regions change between frames
    int sy0 = scope.sy0 - 40, sy1 = scope.sy0 + SCOPE_ROWS * SCOPE_P + 40;
    work.copyRect(base, 0, sy0, W, sy1);
    work.copyRect(base, 0, PROGRESS_Y - 30, W, PROGRESS_Y + 90);
    work.copyRect(base, ONAIR_DOT[0] - 50, ONAIR_DOT[1] - 50, ONAIR_DOT[0] + 50, ONAIR_DOT[1] + 50);

    // scope: draw on a copy of the cover-less screen, show it only inside the panel, keep the cover on top
    Canvas layer = baseNoCover.copyRegion(sy0, sy1);
    dm(layer, 0, scope.sy0 - sy0, scope.bitmap(t), SCOPE_P, OR, 0.5, 0.40);
    for (int y = sy0; y < sy1; y++) for (int x = 0; x < W; x++) {
      int gi = y * W + x, li = (y - sy0) * W + x;
      float a = boxAlpha[gi] * (1 - coverAlpha[gi]);
      if (a <= 0) continue;
      work.r[gi] += (layer.r[li] - work.r[gi]) * a;
      work.g[gi] += (layer.g[li] - work.g[gi]) * a;
      work.b[gi] += (layer.b[li] - work.b[gi]) * a;
    }

    drawProgress(work, t, (int) length);
    drawOnAirPulse(work, t);
    px = work.toPixels(px);
    return px;
  }
}


// ---------- running ffmpeg / ffprobe ----------
String run(String... cmd) {
  try {
    ProcessBuilder pb = new ProcessBuilder(cmd);
    pb.redirectErrorStream(true);
    Process p = pb.start();
    String out = new String(p.getInputStream().readAllBytes(), "UTF-8");
    p.waitFor();
    return out;
  } catch (Exception e) {
    throw new RuntimeException("Couldn't run " + cmd[0] + " - is ffmpeg installed? " + e.getMessage());
  }
}

// decode a stretch of audio to mono float samples
float[] decode(File f, float from, float seconds, int sr) {
  try {
    ProcessBuilder pb = new ProcessBuilder(FFMPEG, "-v", "error", "-ss", str(from), "-t", str(seconds), "-i", f.getAbsolutePath(),
      "-ac", "1", "-ar", str(sr), "-f", "f32le", "-");
    pb.redirectError(ProcessBuilder.Redirect.INHERIT);
    Process p = pb.start();
    byte[] raw = p.getInputStream().readAllBytes();
    p.waitFor();
    java.nio.FloatBuffer fb = java.nio.ByteBuffer.wrap(raw).order(java.nio.ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
    float[] out = new float[fb.remaining()];
    fb.get(out);
    return out;
  } catch (Exception e) {
    throw new RuntimeException("Couldn't decode " + f.getName() + ": " + e.getMessage());
  }
}

void findTools() {
  String[] dirs = { "/opt/homebrew/bin/", "/usr/local/bin/", "/usr/bin/", "C:\\ffmpeg\\bin\\" };
  if (FFMPEG.length() == 0) for (String d : dirs) if (new File(d + "ffmpeg").exists() || new File(d + "ffmpeg.exe").exists()) { FFMPEG = d + "ffmpeg"; break; }
  if (FFPROBE.length() == 0) for (String d : dirs) if (new File(d + "ffprobe").exists() || new File(d + "ffprobe.exe").exists()) { FFPROBE = d + "ffprobe"; break; }
  if (FFMPEG.length() == 0) FFMPEG = "ffmpeg";
  if (FFPROBE.length() == 0) FFPROBE = "ffprobe";
  println("MFYN: using " + FFMPEG);
}
