"""Step 2a, Make Episode Content: an episode's baseline content in one run.

Double-click scripts\\make_content.cmd (or its desktop shortcut), or run:

    python -m intake.content                    # the newest episode in MFYN_Show_Archive
    python -m intake.content --episode NAME     # the episode whose folder name contains NAME
    python -m intake.content --skip-handles     # don't stop to confirm Instagram handles

In one go it makes the episode's
  1. archive cover and YouTube playlist image (intake.archive_cover), in its folder in MFYN_Show_Archive;
  2. ON AIR video posts (intake.reels) and their captions (intake.captions), in MFYN_Posts;
  3. Album Stories (intake.stories), one per artist in the episode, in MFYN_Stories.
Anything already made is skipped, so re-running is safe. See
docs/02a-make-episode-content.md.
"""
import argparse
import logging
import random
import sys

from . import archive_cover, catalog, config, episode, google_auth, handles, reels, stories

log = logging.getLogger("content")


def main(argv=None, ask=input, say=print, rng=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    parser.add_argument("--skip-handles", action="store_true", help="don't stop to confirm Instagram handles")
    args = parser.parse_args(argv)
    reels.setup_logging(config.CONTENT_LOG_FILE)
    rng = rng or random.Random()

    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1
    tracks = [reels.read_track(p) for p in ep.tracks()]
    if not tracks:
        log.error("'%s' has no audio files in its Tracks folder.", ep.folder.name)
        return 1

    say(f"\nEpisode: {ep.folder.name}  (airs {ep.air_date:%A %d %B %Y})")
    for t in tracks:
        say(f"  {t.artist} - {t.title}")
    if ask(f"\nMake the content for these {len(tracks)} track(s)? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        return 0

    # 1. The archive cover and YouTube playlist image, in the episode folder.
    episodes = episode.all_in(config.SHOW_ARCHIVE_DIR)
    cover_failed = archive_cover.number_for(ep, episodes) is not None \
        and archive_cover.make(ep, episodes, ask=ask) is None

    try:
        cat = catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        log.warning("Couldn't open the %s sheet (%s). The posts and Stories will be made without Instagram "
                    "handles or album links.", config.ARTISTS_SHEET, e)
        cat = None

    # Which album, and which of its tracks, each artist's Story features.
    if config.LIBRARY_DIR.is_dir():
        picks = stories.for_episode(tracks, stories.albums(config.LIBRARY_DIR), rng, stories.done_artists(ep))
    else:
        log.error("Library %s not found, so no Album Stories can be made.", config.LIBRARY_DIR)
        picks = None

    # Instagram handles, once for everyone in the posts and the Stories.
    if cat and not args.skip_handles:
        artists, labels = [t.artist for t in tracks], reels.labels_for(tracks, cat)
        for folder, album, index, _ in picks or []:
            who = stories.details(folder, album, album[index], cat, config.STORY_SECONDS, ep)
            artists.append(who["artist"])
            if who["label"] and who["label"] != "Self-released":
                labels.append(who["label"])
        say("\nInstagram handles. Only ones that aren't confirmed yet are asked about.")
        handles.confirm(cat.artists, list(dict.fromkeys(artists)), "artist", ask=ask)
        handles.confirm(cat.labels, list(dict.fromkeys(labels)), "label", ask=ask)

    # 2. The ON AIR video posts, then their captions.
    made, failed, written, posts_dir = reels.make_posts(ep, tracks, cat)

    # 3. An Album Story for each artist who doesn't have one yet.
    stories_made = stories_failed = 0
    for folder, album, index, artist in picks or []:
        if stories.make(folder, album, index, ep, cat, episode_artist=artist):
            stories_made += 1
        else:
            stories_failed += 1

    log.info("\nDone with %s:", ep.folder.name)
    if cover_failed:
        log.error("  The archive cover wasn't made. Scroll up for Processing's messages.")
    log.info("  %d video post(s) made, %d failed, %d caption(s) written, in %s", made, failed, written, posts_dir)
    if picks is None:
        log.error("  No Album Stories: the library wasn't found.")
    else:
        log.info("  %d Album Story(ies) made, %d failed, in %s", stories_made, stories_failed,
                 config.STORIES_DIR / ep.folder.name)
    return 1 if cover_failed or failed or stories_failed or picks is None else 0


if __name__ == "__main__":
    sys.exit(main())
