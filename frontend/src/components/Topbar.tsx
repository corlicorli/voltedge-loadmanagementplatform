import { Github, RefreshCw, Search } from "lucide-react";

const REPO_URL = "https://github.com/corlicorli/voltedge-loadmanagementplatform";

interface Props {
  query: string;
  onQuery: (value: string) => void;
  updatedLabel: string | null;
  onRefresh: () => void;
}

export function Topbar({ query, onQuery, updatedLabel, onRefresh }: Props) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-4 border-b bg-card/80 px-4 py-3 backdrop-blur lg:px-6">
      <div className="hidden text-sm font-semibold sm:block">Dashboard</div>
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search sessions by charger…"
          className="w-full rounded-lg border bg-background py-2 pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40"
        />
      </div>
      <div className="ml-auto flex items-center gap-3 text-[13px] text-muted-foreground">
        <span className="hidden items-center gap-2 sm:flex">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-stable opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-stable" />
          </span>
          Live · 5s
        </span>
        {updatedLabel && <span className="hidden md:inline">Updated {updatedLabel}</span>}
        <button
          onClick={onRefresh}
          title="Refresh"
          className="grid h-9 w-9 place-items-center rounded-lg border bg-background hover:bg-secondary"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
        <a
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          title="Source"
          className="grid h-9 w-9 place-items-center rounded-lg border bg-background hover:bg-secondary"
        >
          <Github className="h-4 w-4" />
        </a>
        <div className="h-9 w-9 rounded-full bg-primary" />
      </div>
    </header>
  );
}
