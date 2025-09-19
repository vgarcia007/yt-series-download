# yt-series-download

A small script that downloads YouTube episodes from a CSV using `yt-dlp` and puts them into season folders.

## What it does
- Reads a semicolon-separated CSV with columns: `Episode;Title;Link` (also accepts `Titel` and `URL`)
- Downloads each URL in best quality
- Saves files as: `<CSV name>/Season 01/S01E03 - Title.mkv`
- On re-run:
  - File ≥ 10 MB: skipped
  - File < 10 MB: re-downloaded (overwritten)
  - Only a `.part` file exists: re-downloaded

## Requirements
- Python 3.8+
- yt-dlp
- ffmpeg (for merging video/audio)

Install examples:
- yt-dlp: `python3 -m pip install -U yt-dlp`
- ffmpeg (Debian/Ubuntu): `sudo apt install ffmpeg`

## CSV format
Header and semicolons are important. Examples (both work):

```
Episode;Title;Link
S01E01;Chicken;https://www.youtube.com/watch?v=...
S01E02;Sheep;https://www.youtube.com/watch?v=...
```

or

```
Episode;Titel;Link
S01E01;Chicken;https://www.youtube.com/watch?v=...
```

Fields:
- Episode: e.g. `S01E03`
- Title/Titel: free text
- Link/URL: YouTube URL

## Usage
From the script folder:

- Default run:
  - `python3 yt_series_download.py "Patchwork Pals.csv"`
- Custom output folder:
  - `python3 yt_series_download.py "Patchwork Pals.csv" --dest "/path/to/folder"`
- Choose a different yt-dlp format:
  - `python3 yt_series_download.py "Patchwork Pals.csv" --format "bestvideo+bestaudio/best"`

Notes:
- The default container is `mkv` (robust, no quality loss).
- Seasons are detected from `Sxx` in the Episode column and stored as `Season xx`.

## Output structure
- Base folder: CSV filename without extension (or `--dest`)
- Season subfolders: `Season 01`, `Season 02`, ...
- Filename: `S01E03 - Title.mkv`

## Tips & troubleshooting
- Update yt-dlp: `python3 -m pip install -U yt-dlp`
- Missing ffmpeg? Install it (see above)
- Quote paths that contain spaces
- If a run was interrupted, just run again — it will continue smartly

## Legal notice
Only download content if you have the rights to do so and follow the platform's terms of service.

## License
No license is provided. You can do what the fuck you want with this code, without restrictions. No warranty or liability.
