import { useEffect, useMemo, useState } from "react";
import type { DownloadJob, DownloadRequest, MediaType, ParseResult } from "../types";

interface Props {
  item: ParseResult;
  job: DownloadJob | undefined;
  onDownload: (req: DownloadRequest) => void;
  isDownloading: boolean;
}

/** Extract base directories from a ParseResult destination. */
function extractBaseDirs(item: ParseResult): {
  moviesDir: string;
  tvshowsDir: string;
} {
  const parts = item.destination.split("/").filter(Boolean);
  if (item.media_type === "movie") {
    // destination = /<movies_dir>/<Movie Folder>/<Movie File> — strip last 2 segments
    const moviesDir = "/" + parts.slice(0, -2).join("/");
    const tvshowsDir =
      moviesDir.replace(/[/\\]movies$/i, "/tvshows") || "/home/pi/tvshows";
    return { moviesDir, tvshowsDir };
  } else {
    const tvshowsDir = "/" + parts.slice(0, -3).join("/");
    const moviesDir =
      tvshowsDir.replace(/[/\\]tvshows$/i, "/movies") || "/home/pi/movies";
    return { moviesDir, tvshowsDir };
  }
}

function buildDestination(
  mediaType: MediaType,
  filename: string,
  item: ParseResult,
  moviesDir: string,
  tvshowsDir: string
): string {
  if (mediaType === "movie") {
    // Jellyfin: Film (Year)/Film (Year).mkv
    const folder = filename.includes(".")
      ? filename.slice(0, filename.lastIndexOf("."))
      : filename;
    return `${moviesDir}/${folder}/${filename}`;
  }
  const title = item.title ?? filename.replace(/\.[^.]+$/, "");
  const season = item.season ?? 1;
  return `${tvshowsDir}/${title}/Season ${String(season).padStart(2, "0")}/${filename}`;
}

/** Split a filename into stem and extension using the raw source filename. */
function splitFilename(rawFilename: string): { ext: string } {
  const lastDot = rawFilename.lastIndexOf(".");
  return { ext: lastDot > 0 ? rawFilename.slice(lastDot) : "" };
}

export function UrlCard({ item, job, onDownload, isDownloading }: Props) {
  const { moviesDir, tvshowsDir } = useMemo(() => extractBaseDirs(item), [item]);

  // Extension is fixed from the raw filename — never editable
  const { ext } = useMemo(() => splitFilename(item.raw_filename), [item.raw_filename]);

  // Stem is the suggested name minus its extension.
  // Guard against ext="" edge case: slice(0, -0) returns "" in JS.
  const initialStem =
    ext.length > 0 && item.suggested_filename.endsWith(ext)
      ? item.suggested_filename.slice(0, -ext.length)
      : item.suggested_filename;

  const [stem, setStem] = useState(initialStem);
  const [mediaType, setMediaType] = useState<MediaType>(item.media_type);
  const [destination, setDestination] = useState(item.destination);
  const [userEditedDest, setUserEditedDest] = useState(false);

  const filename = stem + ext;

  useEffect(() => {
    if (!userEditedDest) {
      setDestination(buildDestination(mediaType, filename, item, moviesDir, tvshowsDir));
    }
  }, [mediaType, filename, userEditedDest, item, moviesDir, tvshowsDir]);

  const isActive = job?.status === "pending" || job?.status === "downloading";
  const canDownload = !isActive && !isDownloading;

  const progressPercent =
    job?.total_bytes && job.total_bytes > 0
      ? Math.round((job.progress_bytes / job.total_bytes) * 100)
      : null;

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/60 p-5 flex flex-col gap-4">
      <p className="text-xs text-zinc-500 font-mono truncate" title={item.raw_filename}>
        {item.raw_filename}
      </p>

      <div className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-400">Filename</span>
          <div className="flex rounded-md border border-zinc-600 bg-zinc-900 overflow-hidden focus-within:ring-2 focus-within:ring-blue-500">
            <input
              type="text"
              value={stem}
              onChange={(e) => {
                // Strip extension if the user accidentally types it into the stem
                const val = e.target.value;
                setStem(
                  ext.length > 0 && val.toLowerCase().endsWith(ext.toLowerCase())
                    ? val.slice(0, -ext.length)
                    : val
                );
              }}
              className="flex-1 min-w-0 bg-transparent px-3 py-2 text-sm text-zinc-100 focus:outline-none"
            />
            <span
              title="Extension — not editable"
              className="flex items-center px-3 text-sm text-zinc-500 bg-zinc-800 border-l border-zinc-700 select-none font-mono shrink-0 cursor-not-allowed"
            >
              {ext}
            </span>
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-400">Type</span>
          <select
            value={mediaType}
            onChange={(e) => {
              setMediaType(e.target.value as MediaType);
              setUserEditedDest(false);
            }}
            className={`rounded-md border bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              !item.guessit_confident ? "border-yellow-500" : "border-zinc-600"
            }`}
          >
            <option value="movie">Movie</option>
            <option value="episode">TV Show</option>
          </select>
          {!item.guessit_confident && (
            <span className="text-xs text-yellow-400">Low confidence — verify type</span>
          )}
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-400">Destination</span>
          <input
            type="text"
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value);
              setUserEditedDest(true);
            }}
            className="rounded-md border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm font-mono text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>
      </div>

      <div className="flex items-center justify-between gap-4">
        <button
          onClick={() =>
            onDownload({ url: item.url, destination, media_type: mediaType })
          }
          disabled={!canDownload}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Download
        </button>

        {job && (
          <div className="flex-1 flex items-center gap-3">
            {job.status === "pending" && (
              <span className="flex items-center gap-2 text-sm text-zinc-400">
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  />
                </svg>
                Pending
              </span>
            )}

            {job.status === "downloading" && (
              <div className="flex-1 flex flex-col gap-1">
                <div className="flex justify-between text-xs text-zinc-400">
                  <span>Downloading…</span>
                  {progressPercent !== null && <span>{progressPercent}%</span>}
                </div>
                <div className="h-2 rounded-full bg-zinc-700 overflow-hidden">
                  {progressPercent !== null ? (
                    <div
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  ) : (
                    <div className="h-full bg-blue-500 animate-pulse w-full" />
                  )}
                </div>
              </div>
            )}

            {job.status === "done" && (
              <span className="flex items-center gap-2 text-sm text-green-400">
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Done
              </span>
            )}

            {job.status === "error" && (
              <span className="text-sm text-red-400 truncate" title={job.error ?? ""}>
                Error: {job.error}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
