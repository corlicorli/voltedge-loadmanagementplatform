import { Activity, Bell, Gauge, TrendingUp } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AreaStatus, Kpis } from "@/lib/api";
import { STATUS_BADGE, STATUS_COLOR, fmtKw } from "@/lib/format";
import { cn } from "@/lib/utils";

export function KpiCards({ status, kpis }: { status: AreaStatus; kpis: Kpis | null }) {
  const util = kpis?.currentUtilisationPct ?? (status.currentLoadKw / status.maxCapacityKw) * 100;
  const gaugeStyle: CSSProperties = {
    background: `conic-gradient(${STATUS_COLOR[status.status]} ${Math.min(util, 100) * 3.6}deg, hsl(var(--muted)) 0deg)`,
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
      <Card className="lg:col-span-2">
        <CardContent className="flex items-center gap-5 p-5">
          <div className="grid h-28 w-28 shrink-0 place-items-center rounded-full" style={gaugeStyle}>
            <div className="grid h-[88px] w-[88px] place-items-center rounded-full bg-card">
              <div className="text-2xl font-bold tabular-nums">{util.toFixed(0)}%</div>
              <div className="text-[11px] text-muted-foreground">load</div>
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Current load</div>
            <div className="text-2xl font-semibold tabular-nums">
              {status.currentLoadKw.toFixed(1)}
              <span className="text-base font-normal text-muted-foreground">
                {" "}
                / {status.maxCapacityKw.toFixed(0)} kW
              </span>
            </div>
            <Badge variant={STATUS_BADGE[status.status]}>{status.status}</Badge>
          </div>
        </CardContent>
      </Card>

      <Kpi icon={<Gauge className="h-4 w-4" />} label="Available capacity" value={fmtKw(status.availableCapacityKw)} />
      <Kpi icon={<Activity className="h-4 w-4" />} label="Active sessions" value={`${status.activeSessionCount}`} />
      <Kpi icon={<TrendingUp className="h-4 w-4" />} label="Peak load · 24h" value={fmtKw(kpis?.peakLoad24HKw ?? null)} />
      <Kpi
        icon={<Bell className="h-4 w-4" />}
        label="Open interventions"
        value={`${kpis?.openInterventions ?? 0}`}
        critical={!!kpis && kpis.openInterventions > 0}
      />
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  critical,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  critical?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
          {icon}
          {label}
        </div>
        <div className={cn("mt-3 text-2xl font-semibold tabular-nums", critical && "text-critical")}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
