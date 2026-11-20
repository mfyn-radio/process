// Streams raw frames straight into ffmpeg (no temp images) and muxes the
// matching stretch of the track as AAC audio.

class Encoder {
  File out;
  Process proc;
  java.io.OutputStream os;
  byte[] buf = new byte[W * H * 3];

  Encoder(File out, File audio, float start, float dur) {
    this.out = out;
    File tmp = new File(out.getAbsolutePath() + ".part.mp4");
    try {
      ProcessBuilder pb = new ProcessBuilder(FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", W + "x" + H, "-r", str(FPS), "-i", "-",
        "-ss", str(start), "-t", str(dur), "-i", audio.getAbsolutePath(),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", tmp.getAbsolutePath());
      pb.redirectError(ProcessBuilder.Redirect.INHERIT);
      pb.redirectOutput(ProcessBuilder.Redirect.INHERIT);
      proc = pb.start();
      os = new java.io.BufferedOutputStream(proc.getOutputStream(), 1 << 20);
    } catch (Exception e) {
      throw new RuntimeException("Couldn't start ffmpeg: " + e.getMessage());
    }
  }

  void write(int[] px) {
    for (int i = 0, j = 0; i < px.length; i++) {
      int c = px[i];
      buf[j++] = (byte) (c >> 16); buf[j++] = (byte) (c >> 8); buf[j++] = (byte) c;
    }
    try { os.write(buf); } catch (Exception e) { throw new RuntimeException("ffmpeg stopped: " + e.getMessage()); }
  }

  void finish() {
    try {
      os.close();
      proc.waitFor();
      File tmp = new File(out.getAbsolutePath() + ".part.mp4");
      if (proc.exitValue() == 0 && tmp.exists()) tmp.renameTo(out);
      else println("MFYN: ffmpeg failed for " + out.getName());
    } catch (Exception e) {
      println("MFYN: " + e.getMessage());
    }
  }
}
