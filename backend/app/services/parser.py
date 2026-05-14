from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import guessit

from app.core.config import settings
from app.models.schemas import MediaType, ParseResult

# Tags commonly appended by encoders/release groups that clutter filenames
_STRIP_PATTERN = re.compile(
    r"\b(BluRay|WEBRip|WEB-DL|HDTV|x264|x265|H\.?264|H\.?265|HEVC|AAC|AC3|"
    r"DTS|10bit|HDR|SDR|REMUX|PROPER|REPACK|1080p|720p|480p|2160p|4K|"
    r"\[.*?\]|\(.*?\))\b",
    re.IGNORECASE,
)


def _strip_tags(stem: str) -> str:
    cleaned = _STRIP_PATTERN.sub("", stem)
    cleaned = re.sub(r"[-_.]+", " ", cleaned).strip()
    return cleaned


def parse_url(url: str) -> ParseResult:
    parsed = urlparse(url)
    raw_filename = unquote(parsed.path.rstrip("/").split("/")[-1])
    stem = Path(raw_filename).stem
    ext = Path(raw_filename).suffix

    guess = guessit.guessit(raw_filename)

    guessit_type = guess.get("type")
    guessit_confident = guessit_type in ("movie", "episode")

    if guessit_type == "episode":
        media_type = MediaType.episode
    else:
        media_type = MediaType.movie

    title: str | None = guess.get("title")
    year: int | None = guess.get("year")
    season: int | None = guess.get("season")
    episode_num: int | None = guess.get("episode")

    if title:
        if media_type == MediaType.movie:
            if year:
                suggested_filename = f"{title} ({year}){ext}"
            else:
                suggested_filename = f"{title}{ext}"
        else:
            s = season if season is not None else 1
            e = episode_num if episode_num is not None else 1
            suggested_filename = f"{title} S{s:02d}E{e:02d}{ext}"
    else:
        suggested_filename = f"{_strip_tags(stem)}{ext}"

    if media_type == MediaType.movie:
        destination = f"{settings.movies_dir}/{suggested_filename}"
    else:
        t = title or _strip_tags(stem)
        s = season if season is not None else 1
        destination = f"{settings.tvshows_dir}/{t}/Season {s:02d}/{suggested_filename}"

    return ParseResult(
        url=url,
        raw_filename=raw_filename,
        suggested_filename=suggested_filename,
        media_type=media_type,
        guessit_confident=guessit_confident,
        destination=destination,
        title=title,
        year=year,
        season=season,
        episode=episode_num,
    )
