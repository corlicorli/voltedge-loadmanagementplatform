import { Activity, Bell, Gauge, TrendingUp, Zap } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AreaStatus, Kpis } from "@/lib/api";
import { STATUS_BADGE, STATUS_COLOR, fmtKw } from "@/lib/format";
import { cn } from "@/lib/utils";

export function KpiCards({ status, kpis }: { status: AreaStatus; kpis: Kpis | null }) {
  const util = kpis?.currentUtilisationPct ?? (status.currentLoadKw / status.maxCapacityKw) * 100;
  const headroom = Math.max(0, 100 - util);
  const peak = kpis?.peakLoad24HKw ?? null;
  const interventions = kpis?.openInterventions ?? 0;

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
      <Card className="col-span-2 lg:col-span-1">
        <CardContent className="p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Zap className="h-4 w-4" />
            Current load
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className="text-3xl font-semibold tabular-nums">{status.currentLoadKw.toFixed(1)}</span>
            <span className="text-sm text-muted-foreground">/ {status.maxCapacityKw.toFixed(0)} kW</span>
          </div>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-[width] duration-500"
              style={{ width: `${Math.min(util, 100)}%`, backgroundColor: STATUS_COLOR[status.status] }}
            />
          </div>
          <div className="mt-3">
            <Badge variant={STATUS_BADGE[status.status]}>{status.status}</Badge>
          </div>
        </CardContent>
      </Card>

      <Stat
        icon={<Gauge className="h-4 w-4" />}
        label="Available capacity"
        value={fmtKw(status.availableCapacityKw)}
        sub={`${headroom.toFixed(0)}% headroom`}
      />
      <Stat
        icon={<Activity className="h-4 w-4" />}
        label="Active sessions"
        value={`${status.activeSessionCount}`}
        sub="currently charging"
      />
      <Stat
        icon={<TrendingUp className="h-4 w-4" />}
        label="Peak load · 24h"
        value={fmtKw(peak)}
        sub={peak ? `${((peak / status.maxCapacityKw) * 100).toFixed(0)}% of max` : "no data yet"}
      />
      <Stat
        icon={<Bell className="h-4 w-4" />}
        label="Open interventions"
        value={`${interventions}`}
        sub={interventions > 0 ? "action needed" : "all clear"}
        critical={interventions > 0}
      />
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  sub,
  critical,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  sub: string;
  critical?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {icon}
          {label}
        </div>
        <div className={cn("mt-3 text-3xl font-semibold tabular-nums", critical && "text-critical")}>
          {value}
        </div>
        <div className="mt-1.5 text-xs text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  );
}
