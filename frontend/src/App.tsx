import { UrlCard } from "./components/UrlCard";
import { UrlInput } from "./components/UrlInput";
import { useDownloads } from "./hooks/useDownloads";

export default function App() {
  const { parsedItems, parseMutation, downloadMutation, jobs, jobIds } = useDownloads();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <header className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">mediaflow</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Paste download URLs to parse and queue
          </p>
        </header>

        <section className="mb-10">
          <UrlInput
            onParse={(urls) => parseMutation.mutate(urls)}
            isParsing={parseMutation.isPending}
          />
          {parseMutation.isError && (
            <p className="mt-2 text-sm text-red-400">
              {(parseMutation.error as Error).message}
            </p>
          )}
        </section>

        {parsedItems.length > 0 && (
          <section className="flex flex-col gap-4">
            {parsedItems.map((item) => {
              const jobId = jobIds[item.url];
              const job = jobId ? jobs.find((j) => j.job_id === jobId) : undefined;
              return (
                <UrlCard
                  key={item.url}
                  item={item}
                  job={job}
                  onDownload={(req) => downloadMutation.mutate(req)}
                  isDownloading={
                    downloadMutation.isPending &&
                    downloadMutation.variables?.url === item.url
                  }
                />
              );
            })}
          </section>
        )}
      </div>
    </div>
  );
}
