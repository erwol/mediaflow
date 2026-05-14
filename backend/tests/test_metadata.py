"""
Tests for the metadata enrichment layer (TVMaze and TMDB).

HTTP calls are mocked so these tests run offline.  They document:
- what fields are expected from each API
- how failures are handled
- how enrich_parse_result wires the lookup results into a ParseResult
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import MediaType, ParseResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    from app.services import parser

    monkeypatch.setattr(
        parser,
        "settings",
        SimpleNamespace(movies_dir="/movies", tvshows_dir="/tvshows"),
    )


def _episode_result(**kwargs) -> ParseResult:
    defaults = dict(
        url="https://example.com/Show.S02E03.mkv",
        raw_filename="Show.S02E03.mkv",
        suggested_filename="Show S02E03.mkv",
        media_type=MediaType.episode,
        guessit_confident=True,
        destination="/tvshows/Show/Season 02/Show S02E03.mkv",
        title="Show",
        year=None,
        season=2,
        episode=3,
    )
    return ParseResult(**{**defaults, **kwargs})


def _movie_result(**kwargs) -> ParseResult:
    defaults = dict(
        url="https://example.com/Alien.1979.mkv",
        raw_filename="Alien.1979.mkv",
        suggested_filename="Alien (1979).mkv",
        media_type=MediaType.movie,
        guessit_confident=True,
        destination="/movies/Alien (1979)/Alien (1979).mkv",
        title="Alien",
        year=1979,
        season=None,
        episode=None,
    )
    return ParseResult(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# metadata.lookup_show
# ---------------------------------------------------------------------------


class TestLookupShow:
    @pytest.mark.anyio
    async def test_returns_title_and_year_on_success(self):
        from app.services.metadata import lookup_show

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"name": "Bref", "premiered": "2011-02-07"}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            result = await lookup_show("Bref")

        assert result == {"title": "Bref", "year": 2011}

    @pytest.mark.anyio
    async def test_handles_missing_premiere_date(self):
        from app.services.metadata import lookup_show

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"name": "Some Show", "premiered": None}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            result = await lookup_show("Some Show")

        assert result == {"title": "Some Show", "year": None}

    @pytest.mark.anyio
    async def test_returns_none_on_404(self):
        from app.services.metadata import lookup_show

        mock_resp = MagicMock(status_code=404)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            result = await lookup_show("Nothing")

        assert result is None

    @pytest.mark.anyio
    async def test_returns_none_on_network_error(self):
        from app.services.metadata import lookup_show

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("network down")
            )
            result = await lookup_show("Anything")

        assert result is None


# ---------------------------------------------------------------------------
# metadata.lookup_movie
# ---------------------------------------------------------------------------


class TestLookupMovie:
    @pytest.mark.anyio
    async def test_returns_none_when_no_api_key(self, monkeypatch):
        from app.services import metadata

        monkeypatch.setattr(
            metadata, "settings", SimpleNamespace(tmdb_api_key="")
        )
        result = await metadata.lookup_movie("Alien", 1979)
        assert result is None

    @pytest.mark.anyio
    async def test_returns_title_and_year_on_success(self, monkeypatch):
        from app.services import metadata

        monkeypatch.setattr(
            metadata, "settings", SimpleNamespace(tmdb_api_key="test-key")
        )
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "results": [{"title": "Alien", "release_date": "1979-05-25", "id": 348}]
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            result = await metadata.lookup_movie("Alien", 1979)

        assert result == {"title": "Alien", "year": 1979}

    @pytest.mark.anyio
    async def test_returns_none_on_empty_results(self, monkeypatch):
        from app.services import metadata

        monkeypatch.setattr(
            metadata, "settings", SimpleNamespace(tmdb_api_key="test-key")
        )
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"results": []}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            result = await metadata.lookup_movie("Unknown Film", None)

        assert result is None


# ---------------------------------------------------------------------------
# parser.enrich_parse_result
# ---------------------------------------------------------------------------


class TestEnrichParseResult:
    @pytest.mark.anyio
    async def test_applies_tvmaze_year_to_show_folder(self, monkeypatch):
        """
        Primary use-case: TVMaze fills in the year for the show subfolder.
        Before enrichment: /tvshows/Bref/Season 02/...
        After enrichment:  /tvshows/Bref (2011)/Season 02/...
        """
        from app.services import metadata, parser

        monkeypatch.setattr(
            metadata,
            "lookup_show",
            AsyncMock(return_value={"title": "Bref", "year": 2011}),
        )

        result = _episode_result(title="Bref", year=None)
        enriched = await parser.enrich_parse_result(result)

        assert enriched.year == 2011
        assert enriched.title == "Bref"
        assert "/Bref (2011)/" in enriched.destination
        assert enriched.destination.endswith("Bref S02E03.mkv")

    @pytest.mark.anyio
    async def test_corrects_show_title_from_tvmaze(self, monkeypatch):
        """TVMaze canonical name replaces whatever guessit extracted."""
        from app.services import metadata, parser

        monkeypatch.setattr(
            metadata,
            "lookup_show",
            AsyncMock(return_value={"title": "The Boys", "year": 2019}),
        )

        result = _episode_result(title="Boys", year=None)
        enriched = await parser.enrich_parse_result(result)

        assert enriched.title == "The Boys"
        assert "/The Boys (2019)/" in enriched.destination

    @pytest.mark.anyio
    async def test_falls_back_to_original_when_tvmaze_returns_none(self, monkeypatch):
        """Any lookup failure leaves the ParseResult completely unchanged."""
        from app.services import metadata, parser

        monkeypatch.setattr(
            metadata, "lookup_show", AsyncMock(return_value=None)
        )

        result = _episode_result(title="Bref", year=None)
        enriched = await parser.enrich_parse_result(result)

        assert enriched == result

    @pytest.mark.anyio
    async def test_no_rebuild_when_title_and_year_unchanged(self, monkeypatch):
        """If TVMaze confirms what we already have, no fields change."""
        from app.services import metadata, parser

        monkeypatch.setattr(
            metadata,
            "lookup_show",
            AsyncMock(return_value={"title": "The Boys", "year": 2019}),
        )

        result = _episode_result(title="The Boys", year=2019)
        enriched = await parser.enrich_parse_result(result)

        assert enriched == result

    @pytest.mark.anyio
    async def test_skipped_when_title_is_none(self, monkeypatch):
        """If parse_url couldn't extract a title, skip enrichment entirely."""
        from app.services import metadata, parser

        lookup = AsyncMock()
        monkeypatch.setattr(metadata, "lookup_show", lookup)

        result = _episode_result(title=None)
        enriched = await parser.enrich_parse_result(result)

        assert enriched == result
        lookup.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_tvmaze_without_episode_marker(self, monkeypatch):
        """
        Gladiator-style false positive: guessit labels the file as an episode
        but there is no SxxExx in the filename.  TVMaze must NOT be called.
        """
        from app.services import metadata, parser

        lookup = AsyncMock()
        monkeypatch.setattr(metadata, "lookup_show", lookup)

        result = _episode_result(raw_filename="Gladiator.EXTENDED.2000.1080p.mkv")
        enriched = await parser.enrich_parse_result(result)

        assert enriched == result
        lookup.assert_not_called()

    @pytest.mark.anyio
    async def test_movie_enriched_via_tmdb(self, monkeypatch):
        from app.services import metadata, parser

        monkeypatch.setattr(
            metadata,
            "lookup_movie",
            AsyncMock(return_value={"title": "Alien", "year": 1979}),
        )

        result = _movie_result(title="Alien", year=None)
        enriched = await parser.enrich_parse_result(result)

        assert enriched.year == 1979
        assert enriched.suggested_filename == "Alien (1979).mkv"
        assert enriched.destination == "/movies/Alien (1979)/Alien (1979).mkv"
