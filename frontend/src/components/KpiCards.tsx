import { Activity, BatteryCharging, TrendingUp, Zap } from "lucide-react";
import type { ReactNode } from "react";

import { Sparkline } from "@/components/Sparkline";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AreaStatus, Kpis, LoadSample } from "@/lib/api";
import { STATUS_BADGE, fmtKw } from "@/lib/format";

const ACCENT = {
  blue: "hsl(217 91% 60%)",
  green: "hsl(142 66% 42%)",
  violet: "hsl(258 80% 64%)",
  orange: "hsl(32 95% 48%)",
};

export function KpiCards({
  status,
  kpis,
  series,
}: {
  status: AreaStatus;
  kpis: Kpis | null;
  series: LoadSample[];
}) {
  const tail = series.slice(-40);
  const util = kpis?.currentUtilisationPct ?? (status.currentLoadKw / status.maxCapacityKw) * 100;
  const peak = kpis?.peakLoad24HKw ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric
        icon={<Zap className="h-5 w-5" />}
        color={ACCENT.blue}
        label="Current Load"
        value={`${status.currentLoadKw.toFixed(1)} kW`}
        foot={<Badge variant={STATUS_BADGE[status.status]}>{status.status} · {util.toFixed(0)}%</Badge>}
        spark={tail.map((s) => s.currentLoadKw)}
      />
      <Metric
        icon={<BatteryCharging className="h-5 w-5" />}
        color={ACCENT.green}
        label="Available Capacity"
        value={fmtKw(status.availableCapacityKw)}
        foot={<Foot>{Math.max(0, 100 - util).toFixed(0)}% headroom</Foot>}
        spark={tail.map((s) => s.availableCapacityKw)}
      />
      <Metric
        icon={<Activity className="h-5 w-5" />}
        color={ACCENT.violet}
        label="Active Sessions"
        value={`${status.activeSessionCount}`}
        foot={<Foot>currently charging</Foot>}
        spark={tail.map((s) => s.activeSessionCount)}
      />
      <Metric
        icon={<TrendingUp className="h-5 w-5" />}
        color={ACCENT.orange}
        label="Peak Load · 24h"
        value={fmtKw(peak)}
        foot={<Foot>{peak ? `${((peak / status.maxCapacityKw) * 100).toFixed(0)}% of max` : "no data yet"}</Foot>}
        spark={tail.map((s) => s.currentLoadKw)}
      />
    </div>
  );
}

function Foot({ children }: { children: ReactNode }) {
  return <span className="text-xs text-muted-foreground">{children}</span>;
}

function Metric({
  icon,
  color,
  label,
  value,
  foot,
  spark,
}: {
  icon: ReactNode;
  color: string;
  label: string;
  value: string;
  foot: ReactNode;
  spark: number[];
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3">
          <span
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl"
            style={{ backgroundColor: color.replace(")", " / 0.12)"), color }}
          >
            {icon}
          </span>
          <span className="text-sm font-medium text-muted-foreground">{label}</span>
        </div>
        <div className="mt-3 text-3xl font-semibold tabular-nums">{value}</div>
        <div className="mt-1">{foot}</div>
        <div className="-mx-1 mt-2">{spark.length > 1 && <Sparkline data={spark} color={color} />}</div>
      </CardContent>
    </Card>
  );
}
