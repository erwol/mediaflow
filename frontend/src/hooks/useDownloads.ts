import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getJobs, parseUrl, startDownload } from "../api/client";
import type { DownloadRequest, ParseResult } from "../types";

export function useDownloads() {
  const queryClient = useQueryClient();
  const [parsedItems, setParsedItems] = useState<ParseResult[]>([]);
  const [jobIds, setJobIds] = useState<Record<string, string>>({});

  const parseMutation = useMutation({
    mutationFn: (urls: string[]) => Promise.all(urls.map((url) => parseUrl(url))),
    onSuccess: (results) => {
      setParsedItems((prev) => {
        const existingUrls = new Set(prev.map((p) => p.url));
        const newItems = results.filter((r) => !existingUrls.has(r.url));
        return [...prev, ...newItems];
      });
    },
  });

  const downloadMutation = useMutation({
    mutationFn: (req: DownloadRequest) => startDownload(req),
    onSuccess: (data, req) => {
      setJobIds((prev) => ({ ...prev, [req.url]: data.job_id }));
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn: getJobs,
    refetchInterval: (query) => {
      const activeJobs = (query.state.data ?? []).filter(
        (j) => j.status === "pending" || j.status === "downloading"
      );
      return activeJobs.length > 0 ? 2000 : false;
    },
  });

  return {
    parsedItems,
    parseMutation,
    downloadMutation,
    jobs,
    jobIds,
  };
}
