import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { DailyPeak, LoadStatus, StatusDistribution } from "@/lib/api";
import { STATUS_COLOR, fmtDay } from "@/lib/format";

const peaksConfig: ChartConfig = {
  peak: { label: "Peak" },
  avg: { label: "Avg", color: "hsl(var(--muted-foreground))" },
};

interface PeaksProps {
  data: DailyPeak[];
  warningKw: number;
  criticalKw: number;
  maxKw: number;
}

function CardTitleBar({ children }: { children: ReactNode }) {
  return (
    <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </CardTitle>
  );
}

export function DailyPeaksChart({ data, warningKw, criticalKw, maxKw }: PeaksProps) {
  const rows = data.map((d) => ({ day: fmtDay(d.day), peak: d.peakLoadKw, avg: d.avgLoadKw }));
  const colorFor = (peak: number) =>
    peak >= criticalKw ? STATUS_COLOR.CRITICAL : peak >= warningKw ? STATUS_COLOR.WARNING : STATUS_COLOR.STABLE;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitleBar>
          Daily peak load <span className="font-normal normal-case">· last 7 days (kW)</span>
        </CardTitleBar>
      </CardHeader>
      <CardContent>
        <ChartContainer config={peaksConfig} className="aspect-auto h-[240px] w-full">
          <BarChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="day" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} width={42} domain={[0, Math.ceil(maxKw * 1.05)]} />
            <ChartTooltip content={<ChartTooltipContent unit=" kW" valueFormatter={(v) => v.toFixed(1)} />} />
            <ReferenceLine y={criticalKw} stroke="hsl(var(--critical))" strokeDasharray="4 4" />
            <Bar dataKey="avg" fill="hsl(var(--muted-foreground))" radius={[3, 3, 0, 0]} maxBarSize={22} />
            <Bar dataKey="peak" radius={[3, 3, 0, 0]} maxBarSize={22}>
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

const donutConfig: ChartConfig = {};

export function StatusDonut({ data }: { data: StatusDistribution[] }) {
  const rows = data.map((d) => ({ name: d.status as LoadStatus, value: d.samples, pct: d.pct }));
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitleBar>
          Status distribution <span className="font-normal normal-case">· last 7 days</span>
        </CardTitleBar>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-5">
          <ChartContainer config={donutConfig} className="aspect-square h-[190px] w-[190px]">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent unit=" samples" hideLabel />} />
              <Pie
                data={rows}
                dataKey="value"
                nameKey="name"
                innerRadius={56}
                outerRadius={86}
                paddingAngle={2}
                stroke="none"
              >
                {rows.map((r) => (
                  <Cell key={r.name} fill={STATUS_COLOR[r.name]} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
          <div className="flex-1 space-y-2.5">
            {rows.map((r) => (
              <div key={r.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-[3px]"
                    style={{ backgroundColor: STATUS_COLOR[r.name] }}
                  />
                  {r.name}
                </span>
                <span className="tabular-nums text-muted-foreground">{r.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
