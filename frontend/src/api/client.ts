import type { DownloadJob, DownloadRequest, ParseResult } from "../types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function parseUrl(url: string): Promise<ParseResult> {
  return fetchJson<ParseResult>(`${BASE}/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function startDownload(req: DownloadRequest): Promise<{ job_id: string }> {
  return fetchJson<{ job_id: string }>(`${BASE}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getJob(jobId: string): Promise<DownloadJob> {
  return fetchJson<DownloadJob>(`${BASE}/jobs/${jobId}`);
}

export async function getJobs(): Promise<DownloadJob[]> {
  return fetchJson<DownloadJob[]>(`${BASE}/jobs`);
}
