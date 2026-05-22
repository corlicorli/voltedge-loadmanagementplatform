import { LineChart as LineChartIcon } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ReferenceLine, XAxis, YAxis } from "recharts";

import { CardHeading } from "@/components/CardHeading";
import { Card, CardContent } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { LoadSample } from "@/lib/api";
import { fmtTime } from "@/lib/format";

const config: ChartConfig = { load: { label: "Load", color: "hsl(227 76% 60%)" } };

interface Props {
  data: LoadSample[];
  warningKw: number;
  criticalKw: number;
  maxKw: number;
}

export function LoadTrendChart({ data, warningKw, criticalKw, maxKw }: Props) {
  const rows = data.map((d) => ({ t: fmtTime(d.sampledAt), load: d.currentLoadKw }));
  return (
    <Card>
      <CardHeading
        icon={<LineChartIcon className="h-4 w-4" />}
        color="hsl(227 76% 60%)"
        title="Load Trend"
        right={
          <span className="rounded-full border px-3 py-1 text-xs text-muted-foreground">Last 24h</span>
        }
      />
      <CardContent>
        <ChartContainer config={config} className="aspect-auto h-[280px] w-full">
          <AreaChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <defs>
              <linearGradient id="fillLoad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-load)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--color-load)" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="t" tickLine={false} axisLine={false} minTickGap={48} />
            <YAxis tickLine={false} axisLine={false} width={42} domain={[0, Math.ceil(maxKw * 1.05)]} />
            <ChartTooltip
              content={<ChartTooltipContent unit=" kW" valueFormatter={(v) => v.toFixed(1)} />}
            />
            <ReferenceLine y={warningKw} stroke="hsl(var(--warning))" strokeDasharray="4 4" />
            <ReferenceLine y={criticalKw} stroke="hsl(var(--critical))" strokeDasharray="4 4" />
            <Area
              type="monotone"
              dataKey="load"
              stroke="var(--color-load)"
              strokeWidth={2}
              fill="url(#fillLoad)"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
