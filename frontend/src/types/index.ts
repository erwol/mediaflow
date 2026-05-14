export type MediaType = "movie" | "episode";

export type JobStatus = "pending" | "downloading" | "done" | "error";

export interface ParseResult {
  url: string;
  raw_filename: string;
  suggested_filename: string;
  media_type: MediaType;
  guessit_confident: boolean;
  destination: string;
  title: string | null;
  year: number | null;
  season: number | null;
  episode: number | null;
}

export interface DownloadRequest {
  url: string;
  destination: string;
  media_type: MediaType;
}

export interface DownloadJob {
  job_id: string;
  url: string;
  destination: string;
  status: JobStatus;
  progress_bytes: number;
  total_bytes: number | null;
  error: string | null;
}
