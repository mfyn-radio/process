// The archive cover's design. Every look constant lives here and nowhere else,
// so the cover stays the same from episode to episode and year to year.
//
// All positions and sizes are in 1080 space and are multiplied by SIZE / 1080.
// The source of truth is reference/cover_reference.py in the design handoff.

final int B = 1080;                                // design size

// ---------- colours ----------
final float[] PAPER = { 240, 124, 14 };            // #F07C0E, uncoated orange card. With RANDOM_COLOUR
                                                   // on, each episode gets another hue at this lightness
final float[] INK   = { 20, 18, 16 };              // #141210, warm near-black, never pure black

// ---------- type (Inter, upper case, per-glyph, no kerning) ----------
final int MARGIN = 78;

final String WORDMARK      = "MFYN";
final String WORDMARK_FONT = "InterDisplay-Black.otf";
final float  WORDMARK_SIZE = 330, WORDMARK_TRACK = -14;
final float  WORDMARK_X = 70, WORDMARK_BASELINE = 360;   // ink box x 83-1005, y 120-360

final String SMALL_FONT = "Inter-Bold.otf";
final float  SMALL_SIZE = 38, SMALL_TRACK = 4;
final float  LINE1_BASELINE = 937;                 // NO. 02          ink y 909-937
final float  LINE2_BASELINE = 997;                 // date and label  ink y 969-997

final int SUPERSAMPLE = 4;                         // text is drawn this much larger, then averaged down

// ---------- paper ----------
final float FINE_AMP = 3.2;                        // per-pixel tooth
final float MID_BLUR = 2.2, MID_SCALE = 6, MID_AMP = 3.0;          // mid grain
final float MOTTLE_BLUR = 30, MOTTLE_SCALE = 2, MOTTLE_AMP = 7;    // slow mottling
final int   FIBRES = 900;
final int   FIBRE_LEN_MIN = 6, FIBRE_LEN_MAX = 26;                 // px, upper bound excluded
final int   FIBRE_LEVEL_MIN = 10, FIBRE_LEVEL_MAX = 34;            // out of 255, upper bound excluded
final float FIBRE_BLUR = 0.6, FIBRE_AMP = 22, FIBRE_OFFSET = 0.05;
final int   FIBRE_SIGN = -1;                       // the fibres darken the paper, as on the approved cover
final float LIGHT_BASE = 1.03, LIGHT_FALL = 0.07, LIGHT_X = 0.6, LIGHT_Y = 0.8;  // soft key light, top left
final float VIGNETTE = 0.10;                       // corners about 10% darker

// ---------- ink ----------
final float INK_SPREAD = 0.7;                      // edge softness (blur of the text)
final float INK_DROPOUT = 0.07;                    // how much ink the grain knocks out
final float GRAIN_BLUR = 0.9, GRAIN_THRESHOLD = 0.62;
final float INK_FLOOR = 0.55, INK_PAPER = 0.45, PAPER_REF = 235;  // ink tinted by the paper under it
