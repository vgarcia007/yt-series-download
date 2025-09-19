#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Read a semicolon-separated CSV with header:
Episode;Titel;Link
Example:
S01E03;Chicken;https://www.youtube.com/watch?v=...

Downloads each video in max quality using yt-dlp and stores files as:
<csv_basename>/<Season 01>/<S01E03 - Chicken>.<ext>

Re-run behavior:
- If a matching file already exists and is >= 10 MB: skip
- If it exists but is < 10 MB: force re-download (overwrite)
- If only .part exists: re-download

Requires: pip install yt-dlp (and ffmpeg on the system)
"""

import csv
import re
import sys
import argparse
from pathlib import Path
from yt_dlp import YoutubeDL

MERGE_CONTAINER = "mkv"  # "mkv" is safest; use "mp4" only if you really need it
REDOWNLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def parse_args():
    p = argparse.ArgumentParser(description="Download YouTube videos from CSV into season folders.")
    p.add_argument("csv_file", help="Path to the semicolon-separated CSV (Episode;Titel;Link).")
    p.add_argument("--dest", help="Override base output folder (default: CSV filename without extension).")
    p.add_argument("--format", default="bestvideo+bestaudio/best",
                   help="yt-dlp format string (default: bestvideo+bestaudio/best).")
    return p.parse_args()


def season_from_episode(ep_code: str) -> str:
    """Extract season as two digits from codes like S01E02 -> '01'."""
    if not ep_code:
        return "00"
    m = re.match(r"^S(\d{1,2})E\d{1,2}$", ep_code.strip(), flags=re.IGNORECASE)
    if m:
        return f"{int(m.group(1)):02d}"
    # Fallback: try any Sxx
    m = re.search(r"[sS]\s*(\d{1,2})", ep_code)
    return f"{int(m.group(1)):02d}" if m else "00"


def sanitize_filename(name: str) -> str:
    """Make a string safe for filesystem filenames."""
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name)
    return name


def read_rows(csv_path: Path):
    """Yield (episode, title, url) from the CSV, skipping incomplete lines."""
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ep = (row.get("Episode") or "").strip()
            title = (row.get("Titel") or row.get("Title") or "").strip()
            url = (row.get("Link") or row.get("URL") or "").strip()
            if ep and title and url:
                yield ep, title, url


def find_existing_file(base_no_ext):
    """
    Given a base path without extension, return the first existing completed file
    (ignores .part). Checks common extensions.
    """
    # Try common containers first
    for ext in (".mkv", ".mp4", ".webm", ".m4v", ".mov"):
        p = base_no_ext.with_suffix(ext)
        if p.exists() and not p.name.endswith(".part"):
            return p
    # Fallback: any file starting with base name that is not .part
    for p in base_no_ext.parent.glob(base_no_ext.name + ".*"):
        if not p.name.endswith(".part") and p.is_file():
            return p
    return None


def needs_redownload(base_no_ext):
    """
    Decide whether we should re-download.
    Returns (True/False, existing_file_path or None).
    Rules:
      - If file exists and size >= 10 MB: skip (False)
      - If file exists and size < 10 MB: re-download (True)
      - If only .part exists or nothing: re-download (True)
    """
    existing = find_existing_file(base_no_ext)
    if existing is None:
        # Check if a .part exists -> treat as needs re-download
        part = base_no_ext.with_suffix(base_no_ext.suffix + ".part") if base_no_ext.suffix else None
        return True, None
    try:
        size = existing.stat().st_size
    except OSError:
        return True, existing
    if size >= REDOWNLOAD_SIZE_BYTES:
        return False, existing
    return True, existing


def download_one(url: str, outtmpl: str, fmt: str, overwrite: bool):
    """Download a single URL with a dedicated outtmpl."""
    ydl_opts = {
        "format": fmt,
        "merge_output_format": MERGE_CONTAINER,
        "noplaylist": True,
        "ignoreerrors": True,
        "continuedl": True,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 5,
        "progress_with_newline": True,
        "quiet": False,
        "no_warnings": True,
        "outtmpl": outtmpl,
        # Overwrite behavior
        "overwrites": overwrite,
        # Safer file names (keep Unicode)
        "restrictfilenames": False,
        "windowsfilenames": False,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main():
    args = parse_args()
    csv_path = Path(args.csv_file).expanduser().resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    base_out = Path(args.dest).expanduser().resolve() if args.dest else csv_path.with_suffix("")
    base_out.mkdir(parents=True, exist_ok=True)

    rows = list(read_rows(csv_path))
    if not rows:
        print("No valid rows found. Expect header 'Episode;Titel;Link' and semicolons.", file=sys.stderr)
        sys.exit(2)

    for ep, title, url in rows:
        season = season_from_episode(ep)         # e.g., "01"
        season_dir = base_out / f"Season {season}"
        season_dir.mkdir(parents=True, exist_ok=True)

        safe_title = sanitize_filename(title)
        safe_ep = sanitize_filename(ep)

        # Desired name: "S01E03 - Chicken"
        filename_no_ext = f"{safe_ep} - {safe_title}"
        base_no_ext = season_dir / filename_no_ext

        # Decide whether to re-download
        redownload, existing_path = needs_redownload(base_no_ext)
        outtmpl = str(base_no_ext) + ".%(ext)s"

        if not redownload:
            print(f"✓ Skipping (already ok ≥10MB): {existing_path.name}")
            continue

        # If a too-small file exists, remove it first to avoid confusion
        if existing_path and existing_path.exists():
            try:
                existing_path.unlink()
                print(f"Removed small file (<10MB): {existing_path.name}")
            except OSError as e:
                print(f"Warning: could not remove {existing_path}: {e}")

        print(f"\n=== Downloading {ep}: {title} ===")
        print(f" -> {outtmpl}")
        try:
            download_one(url, outtmpl, args.format, overwrite=True)
        except Exception as e:
            print(f"Error downloading {ep} ({title}): {e}", file=sys.stderr)

    print("\nAll done.")


if __name__ == "__main__":
    main()
