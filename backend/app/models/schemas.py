from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class MediaType(str, Enum):
    movie = "movie"
    episode = "episode"


class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    done = "done"
    error = "error"


class ParseRequest(BaseModel):
    url: str


class ParseResult(BaseModel):
    url: str
    raw_filename: str
    suggested_filename: str
    media_type: MediaType
    guessit_confident: bool
    destination: str
    title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None


class DownloadRequest(BaseModel):
    url: str
    destination: str
    media_type: MediaType


class DownloadJob(BaseModel):
    job_id: str
    url: str
    destination: str
    status: JobStatus
    progress_bytes: int = 0
    total_bytes: int | None = None
    error: str | None = None
