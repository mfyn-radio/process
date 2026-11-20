// One album: read the tracks' tags, the cover and the featured track's audio,
// draw the player once, then render frames (globe + pulse + seek bar).

class Track {
  File file;
  String title = "", artist = "", albumArtist = "", album = "", date = "";
  int number = 0;
  float length = 0;
}

class Album {
  File folder;
  ArrayList<Track> tracks = new ArrayList<Track>();
  Track featured;
  int featuredIdx = 0;
  String album = "", artist = "", released = "";
  float start, dur;

  Layer player;        // the finished player, without the seek fill/knob (alpha = where the player is)
  Layer work;          // per-frame copy of the seek-bar strip
  float[] occ;         // how much of the globe's light the player blocks around itself
  float[] wrapMask;    // where globe light spills onto the player's edges
  float[] outsHalf, outsHalfBlur;   // half-res "not player" mask for the light wrap
  float[] grain;
  float[] pulse;
  Globe globe;
  float[] bg = new float[W * H];
  int[] px;

  Album(File dir) {
    folder = dir;
    for (File f : audioFiles(dir)) tracks.add(readTrack(f));
    java.util.Collections.sort(tracks, new java.util.Comparator<Track>() {
      public int compare(Track a, Track b) {
        if (a.number != b.number) return a.number - b.number;
        return a.file.getName().compareTo(b.file.getName());
      }
    });
    for (Track t : tracks) if (t.title.length() == 0) t.title = t.file.getName().replaceAll("\\.[^.]+$", "");
    Track first = tracks.get(0);
    album = first.album.length() > 0 ? first.album : dir.getName();
    artist = first.albumArtist.length() > 0 ? first.albumArtist : (first.artist.length() > 0 ? first.artist : "UNKNOWN ARTIST");
    released = formatDate(first.date);

    pickFeatured();
    dur = min(min(CLIP_SECONDS, 60), featured.length);
    float[] low = decode(featured.file, 0, featured.length + 1, 2000);
    start = START_OVERRIDE >= 0 ? START_OVERRIDE : loudestStart(low, 2000, dur);
    start = constrain(start, 0, max(0, featured.length - dur));
    pulse = buildPulse(featured.file, start, dur);

    PImage cover = findCover(dir, featured, tracks);
    player = buildPlayer(this, cover);
    work = player.copy();
    buildLightMasks();
    globe = new Globe();
  }

  Track readTrack(File f) {
    Track t = new Track();
    t.file = f;
    String json = run(FFPROBE, "-v", "error", "-show_entries", "format=duration:format_tags", "-of", "json", f.getAbsolutePath());
    JSONObject fmt = parseJSONObject(json).getJSONObject("format");
    t.length = parseFloat(fmt.getString("duration"));
    JSONObject tags = fmt.hasKey("tags") ? fmt.getJSONObject("tags") : new JSONObject();
    for (Object k : tags.keys()) {
      String key = ((String) k).toLowerCase().replace(" ", "_");
      String v = tags.getString((String) k).trim();
      if (key.equals("title")) t.title = v;
      else if (key.equals("artist")) t.artist = v;
      else if (key.equals("album_artist") || key.equals("albumartist")) t.albumArtist = v;
      else if (key.equals("album")) t.album = v;
      else if ((key.equals("date") || key.equals("year")) && t.date.length() == 0) t.date = v;
      else if (key.equals("track") || key.equals("tracknumber")) {
        String n = v.split("/")[0].replaceAll("[^0-9]", "");
        if (n.length() > 0) t.number = parseInt(n);
      }
    }
    return t;
  }

  // featured.txt: a track number, or part of the title / file name. Otherwise track 1.
  void pickFeatured() {
    featuredIdx = 0;
    File ft = new File(folder, "featured.txt");
    if (ft.exists()) {
      String[] lines = loadStrings(ft.getAbsolutePath());
      String want = lines != null && lines.length > 0 ? lines[0].trim() : "";
      boolean found = false;
      if (want.matches("\\d+")) {
        int n = parseInt(want);
        for (int i = 0; i < tracks.size(); i++) if (tracks.get(i).number == n) { featuredIdx = i; found = true; break; }
        if (!found && n >= 1 && n <= tracks.size()) { featuredIdx = n - 1; found = true; }
      } else if (want.length() > 0) {
        for (int i = 0; i < tracks.size(); i++) {
          Track t = tracks.get(i);
          if (t.title.toLowerCase().contains(want.toLowerCase()) || t.file.getName().toLowerCase().contains(want.toLowerCase())) { featuredIdx = i; found = true; break; }
        }
      }
      if (!found) println("MFYN: featured.txt didn't match a track (\"" + want + "\"), using track 1");
    } else {
      println("MFYN: no featured.txt in " + folder.getName() + ", featuring track 1");
    }
    featured = tracks.get(featuredIdx);
    println("MFYN: featuring " + featured.title);
  }

  // what the globe light does around the player (fixed for the whole clip)
  void buildLightMasks() {
    float[] m = player.a;
    occ = new float[W * H];
    float[] b = m.clone();
    blurBox3(b, W, H, 38);
    for (int i = 0; i < occ.length; i++) occ[i] = 1 - constrain(b[i] * 1.35, 0, 1) * OCC_STRENGTH;

    wrapMask = new float[W * H];
    float[] inv = new float[W * H];
    for (int i = 0; i < inv.length; i++) inv[i] = 1 - m[i];
    blurBox3(inv, W, H, 10);
    for (int i = 0; i < inv.length; i++) wrapMask[i] = constrain(inv[i] * m[i] * 2.0, 0, 1);

    int hw = W / 2, hh = H / 2;
    outsHalf = new float[hw * hh];
    for (int y = 0; y < hh; y++) for (int x = 0; x < hw; x++) outsHalf[y * hw + x] = 1 - m[(2 * y) * W + 2 * x];
    outsHalfBlur = outsHalf.clone();
    blurBox3(outsHalfBlur, hw, hh, 28);
    for (int i = 0; i < outsHalfBlur.length; i++) outsHalfBlur[i] += 1e-4;

    grain = new float[W * H];
    randomSeed(3);
    for (int i = 0; i < grain.length; i++) grain[i] = randomGaussian();
    gaussian(grain, W, H, 0.6);
    for (int i = 0; i < grain.length; i++) grain[i] *= 2;
  }

  int[] renderFrame(int i) {
    float t = i / (float) FPS;
    float p = pulse[min(i, pulse.length - 1)];
    globe.render(bg, t, p);

    // seek bar: redraw just its strip on top of the stored player
    work.copyRect(player, SEEK_RX0, SEEK_RY0, SEEK_RX1, SEEK_RY1);
    drawSeek(work, min(1.0, (start + t) / featured.length));

    // light wrap source: globe light just outside the player, half res
    int hw = W / 2, hh = H / 2;
    float[] src = new float[hw * hh];
    for (int y = 0; y < hh; y++) for (int x = 0; x < hw; x++) src[y * hw + x] = bg[(2 * y) * W + 2 * x] * outsHalf[y * hw + x];
    blurBox3(src, hw, hh, 28);
    for (int k = 0; k < src.length; k++) src[k] /= outsHalfBlur[k];

    if (px == null) px = new int[W * H];
    for (int y = 0; y < H; y++) {
      boolean seekRow = y >= SEEK_RY0 && y < SEEK_RY1;
      for (int x = 0; x < W; x++) {
        int k = y * W + x;
        Layer L = (seekRow && x >= SEEK_RX0 && x < SEEK_RX1) ? work : player;
        float a = L.a[k];
        float g = bg[k] * (1 - a) * occ[k];
        float r = L.r[k] * a + g, gg = L.g[k] * a + g, b = L.b[k] * a + g;
        float wm = wrapMask[k];
        if (wm > 0) {
          float w = sampleHalf(src, hw, hh, x, y) * wm * WRAP_STRENGTH;
          r += w * (1 - r / 255); gg += w * (1 - gg / 255); b += w * (1 - b / 255);
        }
        float n = grain[k];
        int R = (int) constrain(r + n, 0, 255), G = (int) constrain(gg + n, 0, 255), B = (int) constrain(b + n, 0, 255);
        px[k] = 0xFF000000 | (R << 16) | (G << 8) | B;
      }
    }
    return px;
  }
}


// bilinear sample of a half-res map at full-res pixel (x, y), corners aligned
float sampleHalf(float[] a, int hw, int hh, int x, int y) {
  float fx = x * (hw - 1) / (float) (W - 1), fy = y * (hh - 1) / (float) (H - 1);
  int x0 = (int) fx, y0 = (int) fy;
  int x1 = min(x0 + 1, hw - 1), y1 = min(y0 + 1, hh - 1);
  float tx = fx - x0, ty = fy - y0;
  float top = a[y0 * hw + x0] * (1 - tx) + a[y0 * hw + x1] * tx;
  float bot = a[y1 * hw + x0] * (1 - tx) + a[y1 * hw + x1] * tx;
  return top * (1 - ty) + bot * ty;
}

String formatDate(String d) {
  if (d == null) return "";
  d = d.trim();
  if (d.matches("\\d{4}-\\d{2}-\\d{2}.*")) return d.substring(8, 10) + "." + d.substring(5, 7) + "." + d.substring(0, 4);
  if (d.matches("\\d{4}.*")) return d.substring(0, 4);
  return d;
}

// image files in the album folder first, then artwork embedded in the tracks (featured track first)
PImage findCover(File dir, Track featured, ArrayList<Track> tracks) {
  String[] names = { "cover.jpg", "cover.png", "folder.jpg", "folder.png", "front.jpg", "front.png" };
  for (String n : names) {
    File c = new File(dir, n);
    if (c.exists()) { PImage img = loadImage(c.getAbsolutePath()); if (img != null) return img; }
  }
  File[] all = dir.listFiles();
  if (all != null) for (File c : all) {
    String n = c.getName().toLowerCase();
    if (n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".png")) { PImage img = loadImage(c.getAbsolutePath()); if (img != null) return img; }
  }
  ArrayList<Track> order = new ArrayList<Track>(tracks);
  order.remove(featured);
  order.add(0, featured);
  File tmp = new File(sketchPath("cover_tmp.png"));
  for (Track t : order) {
    tmp.delete();
    run(FFMPEG, "-v", "error", "-y", "-i", t.file.getAbsolutePath(), "-an", "-frames:v", "1", tmp.getAbsolutePath());
    if (tmp.exists() && tmp.length() > 0) { PImage img = loadImage(tmp.getAbsolutePath()); tmp.delete(); if (img != null) return img; }
  }
  println("MFYN: no cover found in " + dir.getName() + ", using a blank one");
  PImage blank = createImage(8, 8, RGB);
  return blank;
}

// low-end loudness of the clip: quick attack, slower release, 0..1 per frame
float[] buildPulse(File f, float start, float dur) {
  int sr = 22050;
  float[] x = lowpass(decode(f, start, dur, sr), sr, PULSE_LOWPASS_HZ);
  int n = round(dur * FPS), hop = sr / FPS;
  float[] e = new float[n];
  for (int i = 0; i < n; i++) {
    double s = 0; int cnt = 0;
    for (int k = i * hop; k < min(x.length, (i + 1) * hop); k++) { s += x[k] * x[k]; cnt++; }
    e[i] = (float) Math.log(Math.sqrt(s / max(1, cnt)) + 1e-6);
  }
  float[] sorted = e.clone();
  java.util.Arrays.sort(sorted);
  float lo = sorted[(int) (0.20 * (n - 1))], hi = sorted[(int) (0.98 * (n - 1))];
  float[] out = new float[n];
  float v = 0;
  for (int i = 0; i < n; i++) {
    float k = pow(constrain((e[i] - lo) / max(1e-6, hi - lo), 0, 1), 1.6);
    v = k > v ? k : v * 0.82 + k * 0.18;
    out[i] = v;
  }
  return out;
}

// the loudest stretch of the track (after the intro, before the outro)
float loudestStart(float[] x, int sr, float dur) {
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
