from __future__ import annotations

import uuid
from pathlib import Path

import httpx

from app.core.config import settings
from app.models.schemas import DownloadJob, DownloadRequest, JobStatus

jobs: dict[str, DownloadJob] = {}


def create_job(req: DownloadRequest) -> DownloadJob:
    job_id = str(uuid.uuid4())
    job = DownloadJob(
        job_id=job_id,
        url=req.url,
        destination=req.destination,
        status=JobStatus.pending,
    )
    jobs[job_id] = job
    return job


async def run_download(job_id: str) -> None:
    job = jobs.get(job_id)
    if job is None:
        return

    job.status = JobStatus.downloading

    try:
        dest = Path(job.destination)
        dest.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.download_timeout,
        ) as client:
            async with client.stream("GET", job.url) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length:
                    job.total_bytes = int(content_length)

                with dest.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        job.progress_bytes += len(chunk)

        job.status = JobStatus.done

    except Exception as exc:
        job.status = JobStatus.error
        job.error = str(exc)
