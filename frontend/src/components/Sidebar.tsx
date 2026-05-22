import { Activity, BarChart3, ExternalLink, FileCode2, Gauge, LayoutDashboard } from "lucide-react";
import type { ReactNode } from "react";

const DOCS_URL = "http://localhost:8000/docs";
const GRAFANA_URL = "http://localhost:3001";
const PROM_URL = "http://localhost:9090";
const REPO_URL = "https://github.com/corlicorli/voltedge-loadmanagementplatform";

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col self-start border-r bg-card lg:sticky lg:top-0 lg:flex lg:h-screen lg:overflow-y-auto">
      <div className="px-5 py-5">
        <div className="text-[15px] font-semibold leading-tight tracking-tight">VoltEdge Mobility A/S</div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">Load Management</div>
      </div>

      <nav className="flex-1 space-y-6 px-3 py-2">
        <Section label="Dashboard">
          <NavItem icon={<LayoutDashboard className="h-4 w-4" />} active>
            Overview
          </NavItem>
          <NavItem icon={<BarChart3 className="h-4 w-4" />} href="#analytics">
            Analytics
          </NavItem>
          <NavItem icon={<Activity className="h-4 w-4" />} href="#sessions">
            Sessions
          </NavItem>
        </Section>

        <Section label="Tools">
          <NavItem icon={<FileCode2 className="h-4 w-4" />} href={DOCS_URL} external>
            API Docs
          </NavItem>
          <NavItem icon={<Gauge className="h-4 w-4" />} href={GRAFANA_URL} external>
            Ops Monitoring
          </NavItem>
          <NavItem icon={<Activity className="h-4 w-4" />} href={PROM_URL} external>
            Metrics
          </NavItem>
          <NavItem icon={<ExternalLink className="h-4 w-4" />} href={REPO_URL} external>
            Source
          </NavItem>
        </Section>
      </nav>

      <div className="m-3 rounded-xl border bg-secondary/60 p-4 text-center">
        <div className="text-xs font-semibold">Load Control Context</div>
        <div className="mt-1 text-[11px] text-muted-foreground">DDD · FastAPI · PostgreSQL</div>
      </div>
    </aside>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function NavItem({
  icon,
  children,
  active,
  href,
  external,
}: {
  icon: ReactNode;
  children: ReactNode;
  active?: boolean;
  href?: string;
  external?: boolean;
}) {
  const cls = `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    active ? "bg-primary/10 text-primary" : "text-foreground/70 hover:bg-secondary hover:text-foreground"
  }`;
  if (href) {
    return (
      <a className={cls} href={href} {...(external ? { target: "_blank", rel: "noreferrer" } : {})}>
        {icon}
        {children}
        {external && <ExternalLink className="ml-auto h-3 w-3 opacity-50" />}
      </a>
    );
  }
  return (
    <div className={cls}>
      {icon}
      {children}
    </div>
  );
}
