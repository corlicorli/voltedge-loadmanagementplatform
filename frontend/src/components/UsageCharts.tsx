import { BarChart3, PieChart as PieChartIcon } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, XAxis, YAxis } from "recharts";

import { CardHeading } from "@/components/CardHeading";
import { Card, CardContent } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { DailyPeak, LoadStatus, StatusDistribution } from "@/lib/api";
import { STATUS_COLOR, fmtDay } from "@/lib/format";

const peaksConfig: ChartConfig = { peak: { label: "Peak" }, avg: { label: "Avg" } };

interface PeaksProps {
  data: DailyPeak[];
  warningKw: number;
  criticalKw: number;
  maxKw: number;
}

export function DailyPeaksChart({ data, warningKw, criticalKw, maxKw }: PeaksProps) {
  const rows = data.map((d) => ({ day: fmtDay(d.day), peak: d.peakLoadKw, avg: d.avgLoadKw }));
  const maxPeak = data.length ? Math.max(...data.map((d) => d.peakLoadKw)) : 0;
  const colorFor = (peak: number) =>
    peak >= criticalKw ? STATUS_COLOR.CRITICAL : peak >= warningKw ? STATUS_COLOR.WARNING : STATUS_COLOR.STABLE;

  return (
    <Card>
      <CardHeading icon={<BarChart3 className="h-4 w-4" />} color="hsl(0 0% 16%)" title="Daily Peak Load" />
      <CardContent>
        <div className="mb-1 flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums">{maxPeak.toFixed(1)} kW</span>
          <span className="text-xs text-muted-foreground">highest peak · last 7 days</span>
        </div>
        <ChartContainer config={peaksConfig} className="aspect-auto h-[210px] w-full">
          <BarChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="day" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} width={42} domain={[0, Math.ceil(maxKw * 1.05)]} />
            <ChartTooltip content={<ChartTooltipContent unit=" kW" valueFormatter={(v) => v.toFixed(1)} />} />
            <ReferenceLine y={criticalKw} stroke="hsl(var(--critical))" strokeDasharray="4 4" />
            <Bar dataKey="avg" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} maxBarSize={24} />
            <Bar dataKey="peak" radius={[4, 4, 0, 0]} maxBarSize={24}>
              {rows.map((r) => (
                <Cell key={r.day} fill={colorFor(r.peak)} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

// Donut is the one exception to the monochrome palette: subtle orange / red for
// WARNING / CRITICAL so the health split reads at a glance. STABLE stays grey.
const DONUT_COLOR: Record<LoadStatus, string> = {
  STABLE: "hsl(0 0% 72%)",
  WARNING: "hsl(30 72% 55%)",
  CRITICAL: "hsl(2 66% 55%)",
};

const donutConfig: ChartConfig = {};

export function StatusDonut({ data }: { data: StatusDistribution[] }) {
  const rows = data.map((d) => ({ name: d.status as LoadStatus, value: d.samples, pct: d.pct }));
  return (
    <Card>
      <CardHeading icon={<PieChartIcon className="h-4 w-4" />} color="hsl(0 0% 16%)" title="Status Distribution" />
      <CardContent>
        <div className="flex items-center gap-5">
          <ChartContainer config={donutConfig} className="aspect-square h-[180px] w-[180px]">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent unit=" samples" hideLabel />} />
              <Pie
                data={rows}
                dataKey="value"
                nameKey="name"
                innerRadius={54}
                outerRadius={84}
                paddingAngle={2}
                stroke="none"
              >
                {rows.map((r) => (
                  <Cell key={r.name} fill={DONUT_COLOR[r.name]} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
          <div className="flex-1 space-y-3">
            {rows.map((r) => (
              <div key={r.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-[3px]" style={{ backgroundColor: DONUT_COLOR[r.name] }} />
                  {r.name}
                </span>
                <span className="font-medium tabular-nums">{r.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
