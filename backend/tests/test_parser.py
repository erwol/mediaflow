"""
Unit tests for the URL parser.

These tests document the expected behaviour for filename detection and
Jellyfin-compatible path generation. They use a fake settings object so
no environment variables or .env file are required.
"""
from types import SimpleNamespace

import pytest

from app.models.schemas import MediaType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _url(filename: str) -> str:
    """Wrap a filename in a Sonicbit-style URL (the primary source format)."""
    return f"https://dl60.sonicb.it/file/dl2/sometoken/{filename}"


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Replace live settings with predictable test paths."""
    from app.services import parser

    monkeypatch.setattr(
        parser,
        "settings",
        SimpleNamespace(movies_dir="/movies", tvshows_dir="/tvshows"),
    )


# ---------------------------------------------------------------------------
# Episode regex — _EPISODE_RE
# ---------------------------------------------------------------------------


class TestEpisodeRegex:
    def test_standard_uppercase(self):
        from app.services.parser import _EPISODE_RE

        m = _EPISODE_RE.search("Show.Name.S02E03.mkv")
        assert m is not None
        assert m.group(1) == "02"
        assert m.group(2) == "03"

    def test_no_separator_before_marker(self):
        """guessit misses this; the regex must not."""
        from app.services.parser import _EPISODE_RE

        m = _EPISODE_RE.search("BrefS02E03BrefItsaMatter")
        assert m is not None
        assert m.group(1) == "02"
        assert m.group(2) == "03"

    def test_lowercase(self):
        from app.services.parser import _EPISODE_RE

        m = _EPISODE_RE.search("show.s01e04.mkv")
        assert m is not None
        assert m.group(1) == "01"
        assert m.group(2) == "04"

    def test_single_digit_season_and_episode(self):
        from app.services.parser import _EPISODE_RE

        m = _EPISODE_RE.search("Show.S1E4.mkv")
        assert m is not None
        assert m.group(1) == "1"
        assert m.group(2) == "4"

    def test_no_match_for_movie(self):
        from app.services.parser import _EPISODE_RE

        assert _EPISODE_RE.search("The.Matrix.1999.1080p.mkv") is None


# ---------------------------------------------------------------------------
# Domain-tag and codec stripping — _strip_tags
# ---------------------------------------------------------------------------


class TestStripTags:
    def test_strips_x_to(self):
        from app.services.parser import _strip_tags

        result = _strip_tags("ShowName.S01E01.WEBEZTVx.to")
        assert ".to" not in result
        assert "x to" not in result

    def test_strips_eztv_domain(self):
        from app.services.parser import _strip_tags

        result = _strip_tags("Show.S01E01.eztv.re")
        assert "eztv" not in result

    def test_strips_codec_and_quality_tags(self):
        from app.services.parser import _strip_tags

        result = _strip_tags("Show.1080p.WEB-DL.x265.AAC")
        assert "1080p" not in result
        assert "WEB" not in result
        assert "x265" not in result

    def test_replaces_separators_with_spaces(self):
        from app.services.parser import _strip_tags

        assert _strip_tags("The.Boys") == "The Boys"
        assert _strip_tags("The-Boys") == "The Boys"
        assert _strip_tags("The_Boys") == "The Boys"


# ---------------------------------------------------------------------------
# parse_url — episode detection
# ---------------------------------------------------------------------------


class TestParseEpisode:
    def test_bref_no_separator(self):
        """
        Real-world case: Sonicbit URL for Bref S02E03.
        guessit misses the episode because there are no separators around S02E03.
        The regex override must catch it and extract the title from the prefix.
        """
        from app.services.parser import parse_url

        result = parse_url(
            _url(
                "BrefS02E03BrefItsaMatterofPerspective720pDSNPWEB-DLDD51H264"
                "-playWEBEZTVx.to.mkv"
            )
        )
        assert result.media_type == "episode"
        assert result.guessit_confident is True
        assert result.season == 2
        assert result.episode == 3
        assert result.title == "Bref"
        assert result.suggested_filename == "Bref S02E03.mkv"
        assert result.destination == "/tvshows/Bref/Season 02/Bref S02E03.mkv"

    def test_standard_episode_with_dots(self):
        from app.services.parser import parse_url

        result = parse_url(_url("The.Boys.S05E01.1080p.WEB-DL.mkv"))
        assert result.media_type == "episode"
        assert result.guessit_confident is True
        assert result.season == 5
        assert result.episode == 1
        assert result.title == "The Boys"
        assert result.suggested_filename == "The Boys S05E01.mkv"
        assert result.destination == (
            "/tvshows/The Boys/Season 05/The Boys S05E01.mkv"
        )

    def test_episode_destination_uses_year_when_known(self):
        """Show folder includes year when guessit or regex yields one."""
        from app.services.parser import parse_url

        # Some filenames embed the year alongside the episode code
        result = parse_url(_url("Bref.2011.S02E03.mkv"))
        assert result.media_type == "episode"
        assert result.year == 2011
        assert "/Bref (2011)/" in result.destination

    def test_extension_preserved(self):
        from app.services.parser import parse_url

        result = parse_url(_url("Show.S01E01.720p.mkv"))
        assert result.suggested_filename.endswith(".mkv")
        assert result.destination.endswith(".mkv")


# ---------------------------------------------------------------------------
# parse_url — movie detection
# ---------------------------------------------------------------------------


class TestParseMovie:
    def test_movie_with_year(self):
        from app.services.parser import parse_url

        result = parse_url(_url("The.Boy.and.the.Heron.2023.1080p.BluRay.mkv"))
        assert result.media_type == "movie"
        assert result.guessit_confident is True
        assert result.year == 2023
        assert result.suggested_filename == "The Boy and the Heron (2023).mkv"
        # Jellyfin: own subfolder with the same name as the file
        assert result.destination == (
            "/movies/The Boy and the Heron (2023)/The Boy and the Heron (2023).mkv"
        )

    def test_movie_without_year(self):
        from app.services.parser import parse_url

        result = parse_url(_url("Alien.1080p.BluRay.mkv"))
        assert result.media_type == "movie"
        assert result.suggested_filename == "Alien.mkv"
        assert result.destination == "/movies/Alien/Alien.mkv"

    def test_real_world_movie(self):
        """The actual file that triggered this fix."""
        from app.services.parser import parse_url

        result = parse_url(
            _url("Remarkably.Bright.Creatures.2026.1080p.WEBRip.x265.10bit.AAC5.1-LAMA.mp4")
        )
        assert result.media_type == "movie"
        assert result.year == 2026
        assert result.suggested_filename == "Remarkably Bright Creatures (2026).mp4"
        assert result.destination == (
            "/movies/Remarkably Bright Creatures (2026)"
            "/Remarkably Bright Creatures (2026).mp4"
        )


# ---------------------------------------------------------------------------
# parse_url — filename extraction from URL
# ---------------------------------------------------------------------------


class TestFilenameExtraction:
    def test_last_path_segment_is_used(self):
        from app.services.parser import parse_url

        result = parse_url("https://dl60.sonicb.it/file/dl2/token/Movie.2023.mkv")
        assert result.raw_filename == "Movie.2023.mkv"

    def test_url_percent_encoding_decoded(self):
        from app.services.parser import parse_url

        result = parse_url("https://example.com/The%20Matrix%20(1999).mkv")
        assert result.raw_filename == "The Matrix (1999).mkv"

    def test_trailing_slash_ignored(self):
        from app.services.parser import parse_url

        result = parse_url("https://example.com/Movie.2023.mkv/")
        assert result.raw_filename == "Movie.2023.mkv"


# ---------------------------------------------------------------------------
# Pure helpers — _build_suggested_filename, _build_destination
# ---------------------------------------------------------------------------


class TestBuildHelpers:
    def test_movie_suggested_filename_with_year(self):
        from app.services.parser import _build_suggested_filename

        assert (
            _build_suggested_filename(MediaType.movie, "Alien", 1979, None, None, ".mkv")
            == "Alien (1979).mkv"
        )

    def test_movie_suggested_filename_without_year(self):
        from app.services.parser import _build_suggested_filename

        assert (
            _build_suggested_filename(MediaType.movie, "Alien", None, None, None, ".mkv")
            == "Alien.mkv"
        )

    def test_episode_suggested_filename(self):
        from app.services.parser import _build_suggested_filename

        assert (
            _build_suggested_filename(
                MediaType.episode, "The Boys", None, 5, 1, ".mkv"
            )
            == "The Boys S05E01.mkv"
        )

    def test_movie_destination_has_subfolder(self):
        from app.services.parser import _build_destination

        dest = _build_destination(MediaType.movie, "Alien (1979).mkv", "Alien", 1979, None)
        assert dest == "/movies/Alien (1979)/Alien (1979).mkv"

    def test_episode_destination_with_year(self):
        from app.services.parser import _build_destination

        dest = _build_destination(
            MediaType.episode, "Bref S02E03.mkv", "Bref", 2011, 2
        )
        assert dest == "/tvshows/Bref (2011)/Season 02/Bref S02E03.mkv"

    def test_episode_destination_without_year(self):
        from app.services.parser import _build_destination

        dest = _build_destination(
            MediaType.episode, "Bref S02E03.mkv", "Bref", None, 2
        )
        assert dest == "/tvshows/Bref/Season 02/Bref S02E03.mkv"
