import { useState } from "react";

interface Props {
  onParse: (urls: string[]) => void;
  isParsing: boolean;
}

export function UrlInput({ onParse, isParsing }: Props) {
  const [value, setValue] = useState("");

  function handleParse() {
    const urls = value
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (urls.length === 0) return;
    onParse(urls);
    setValue("");
  }

  return (
    <div className="flex flex-col gap-3">
      <textarea
        className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 font-mono text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y min-h-[100px]"
        placeholder="Paste one or more download URLs, one per line…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isParsing}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleParse();
        }}
      />
      <button
        onClick={handleParse}
        disabled={isParsing || !value.trim()}
        className="self-start flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isParsing && (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        )}
        {isParsing ? "Parsing…" : "Parse"}
      </button>
    </div>
  );
}
