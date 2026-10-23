"""Adding albums to MFYN_Library (a local folder synced to Google Drive)."""
import re
import shutil
import zipfile

PARTIAL_PREFIX = ".partial - "
# Not allowed in Windows file names.
UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def clean(name):
    name = UNSAFE.sub("_", name)
    return re.sub(r"\s+", " ", name).strip(" .")


def add(library_dir, name, downloaded):
    """Unzip an album (or move a single track) into library_dir/name, then
    delete the zip. Works in a `.partial - …` folder that's renamed once
    complete, so an interrupted run never leaves a folder that looks done."""
    partial = library_dir / (PARTIAL_PREFIX + name)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    if zipfile.is_zipfile(downloaded):
        with zipfile.ZipFile(downloaded) as zf:
            zf.extractall(partial)
        downloaded.unlink()
    else:
        shutil.move(downloaded, partial / downloaded.name)
    partial.rename(library_dir / name)
    return sorted(p for p in (library_dir / name).rglob("*") if p.is_file())
