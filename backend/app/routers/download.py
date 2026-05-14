from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import DownloadJob, DownloadRequest
from app.services import downloader

router = APIRouter()


@router.post("/api/download")
async def start_download(
    req: DownloadRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    job = downloader.create_job(req)
    background_tasks.add_task(downloader.run_download, job.job_id)
    return {"job_id": job.job_id}


@router.get("/api/jobs/{job_id}", response_model=DownloadJob)
async def get_job(job_id: str) -> DownloadJob:
    job = downloader.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/jobs", response_model=list[DownloadJob])
async def list_jobs() -> list[DownloadJob]:
    return list(reversed(list(downloader.jobs.values())))
