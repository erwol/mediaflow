from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import guessit

from app.core.config import settings
from app.models.schemas import MediaType, ParseResult
from app.services import metadata as _metadata

log = logging.getLogger(__name__)

# Codec / quality / group tags to strip from fallback titles
_STRIP_PATTERN = re.compile(
    r"\b(BluRay|WEBRip|WEB-DL|HDTV|x264|x265|H\.?264|H\.?265|HEVC|AAC|AC3|"
    r"DTS|10bit|HDR|SDR|REMUX|PROPER|REPACK|1080p|720p|480p|2160p|4K|"
    r"\[.*?\]|\(.*?\))\b",
    re.IGNORECASE,
)

# Site domain tags appended to filenames, e.g. "x.to", "eztv.re", "yts.mx"
_DOMAIN_TAG_RE = re.compile(r"\.[a-z]{1,8}\.[a-z]{2,4}$", re.IGNORECASE)

# Unambiguous episode marker — matches S01E01, s1e1, S12E34, etc.
_EPISODE_RE = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,2})")


# ---------------------------------------------------------------------------
# Pure helpers — no I/O, fully testable
# ---------------------------------------------------------------------------


def _strip_tags(stem: str) -> str:
    stem = _DOMAIN_TAG_RE.sub("", stem)
    cleaned = _STRIP_PATTERN.sub("", stem)
    cleaned = re.sub(r"[-_.]+", " ", cleaned).strip()
    return cleaned


def _title_from_prefix(prefix: str) -> str | None:
    """Extract a show title from the portion of a stem before an SxxExx marker."""
    cleaned = re.sub(r"[-_.]+", " ", prefix).strip()
    return cleaned or None


def _build_suggested_filename(
    media_type: MediaType,
    title: str,
    year: int | None,
    season: int | None,
    episode: int | None,
    ext: str,
) -> str:
    if media_type == MediaType.movie:
        return f"{title} ({year}){ext}" if year else f"{title}{ext}"
    s = season if season is not None else 1
    e = episode if episode is not None else 1
    return f"{title} S{s:02d}E{e:02d}{ext}"


def _build_destination(
    media_type: MediaType,
    suggested_filename: str,
    title: str,
    year: int | None,
    season: int | None,
) -> str:
    if media_type == MediaType.movie:
        # Jellyfin: Film (Year)/Film (Year).mkv
        dot = suggested_filename.rfind(".")
        movie_folder = suggested_filename[:dot] if dot > 0 else suggested_filename
        return f"{settings.movies_dir}/{movie_folder}/{suggested_filename}"
    s = season if season is not None else 1
    # Jellyfin: include year in show folder when known, e.g. "Bref (2011)"
    show_folder = f"{title} ({year})" if year else title
    return f"{settings.tvshows_dir}/{show_folder}/Season {s:02d}/{suggested_filename}"


# ---------------------------------------------------------------------------
# Main parse (sync, pure — no network calls)
# ---------------------------------------------------------------------------


def parse_url(url: str) -> ParseResult:
    parsed = urlparse(url)
    raw_filename = unquote(parsed.path.rstrip("/").split("/")[-1])
    stem = Path(raw_filename).stem
    ext = Path(raw_filename).suffix

    guess = guessit.guessit(raw_filename)
    guessit_type = guess.get("type")

    title: str | None = guess.get("title")
    year: int | None = guess.get("year")
    season: int | None = guess.get("season")
    episode_num: int | None = guess.get("episode")

    # Direct regex check — SxxExx is unambiguous even when guessit misses it
    # (common with no-separator filenames like "BrefS02E03BrefIts...")
    ep_match = _EPISODE_RE.search(stem)

    if guessit_type == "episode" or ep_match:
        media_type = MediaType.episode
        guessit_confident = True
        if ep_match:
            if season is None:
                season = int(ep_match.group(1))
            if episode_num is None:
                episode_num = int(ep_match.group(2))
            # When guessit missed the episode entirely its title is unreliable
            # (often the full stem). Only trust guessit's title when it also
            # identified the episode type.
            if title is None or guessit_type != "episode":
                title = _title_from_prefix(stem[: ep_match.start()])
    elif guessit_type == "movie":
        media_type = MediaType.movie
        guessit_confident = True
    else:
        media_type = MediaType.movie
        guessit_confident = False

    if title:
        suggested_filename = _build_suggested_filename(
            media_type, title, year, season, episode_num, ext
        )
    else:
        suggested_filename = f"{_strip_tags(stem)}{ext}"

    destination = _build_destination(
        media_type,
        suggested_filename,
        title or _strip_tags(stem),
        year,
        season,
    )

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


# ---------------------------------------------------------------------------
# Async enrichment (network calls, isolated, fails silently)
# ---------------------------------------------------------------------------


async def enrich_parse_result(result: ParseResult) -> ParseResult:
    """
    Enrich a ParseResult with canonical metadata from TVMaze (TV) or TMDB (movies).

    - TV shows: TVMaze is queried only when SxxExx appears in the raw filename.
    - Movies:   TMDB is queried only when TMDB_API_KEY is set in the environment.
    - Any network failure or missing result leaves the original unchanged.
    """
    if not result.title:
        return result

    meta: dict | None = None
    if result.media_type == MediaType.episode:
        # Only call TVMaze when there is an unambiguous SxxExx marker in the raw
        # filename.  Without this guard, guessit false-positives (e.g. "Gladiator"
        # misclassified as episode) would hit TVMaze and return a random TV show.
        if _EPISODE_RE.search(result.raw_filename):
            meta = await _metadata.lookup_show(result.title)
    elif result.media_type == MediaType.movie:
        meta = await _metadata.lookup_movie(result.title, result.year)

    if not meta:
        return result

    title = meta.get("title") or result.title
    year = meta.get("year") or result.year

    # Skip rebuild if nothing actually changed
    if title == result.title and year == result.year:
        return result

    ext = Path(result.raw_filename).suffix
    suggested_filename = _build_suggested_filename(
        result.media_type, title, year, result.season, result.episode, ext
    )
    destination = _build_destination(
        result.media_type, suggested_filename, title, year, result.season
    )

    log.debug("Enriched %r → title=%r year=%r", result.raw_filename, title, year)

    return result.model_copy(
        update={
            "title": title,
            "year": year,
            "suggested_filename": suggested_filename,
            "destination": destination,
        }
    )
