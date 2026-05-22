import type { CSSProperties } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Forecast, LoadSample } from "../lib/api";
import { fmtTime } from "../lib/format";

const AXIS = "#8a98b5";
const GRID = "#243049";
const TOOLTIP: CSSProperties = {
  background: "#1a2236",
  border: "1px solid #243049",
  borderRadius: 10,
  fontSize: 12,
  color: "#e7ecf5",
};

interface TrendProps {
  data: LoadSample[];
  warningKw: number;
  criticalKw: number;
  maxKw: number;
}

export function LoadTrendChart({ data, warningKw, criticalKw, maxKw }: TrendProps) {
  const rows = data.map((d) => ({ t: fmtTime(d.sampledAt), load: d.currentLoadKw }));
  return (
    <div className="card">
      <h2>
        Load trend <span className="hint">last 24h · kW</span>
      </h2>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={rows} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="loadFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="t" stroke={AXIS} fontSize={11} tickLine={false} minTickGap={44} />
          <YAxis
            stroke={AXIS}
            fontSize={11}
            tickLine={false}
            width={42}
            domain={[0, Math.ceil(maxKw * 1.05)]}
          />
          <Tooltip
            contentStyle={TOOLTIP}
            labelStyle={{ color: AXIS }}
            formatter={(v) => [`${(v as number).toFixed(1)} kW`, "Load"]}
          />
          <ReferenceLine y={warningKw} stroke="#f59e0b" strokeDasharray="4 4" />
          <ReferenceLine y={criticalKw} stroke="#ef4444" strokeDasharray="4 4" />
          <Area type="monotone" dataKey="load" stroke="#22d3ee" strokeWidth={2} fill="url(#loadFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

interface ForecastProps {
  forecast: Forecast;
  warningKw: number;
  criticalKw: number;
}

export function ForecastChart({ forecast, warningKw, criticalKw }: ForecastProps) {
  const rows = forecast.points.map((p) => ({ t: fmtTime(p.timestamp), load: p.predictedLoadKw }));
  return (
    <div className="card">
      <h2>
        Predictive forecast <span className="hint">next {forecast.horizonHours}h · {forecast.method}</span>
      </h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="t" stroke={AXIS} fontSize={11} tickLine={false} minTickGap={36} />
          <YAxis
            stroke={AXIS}
            fontSize={11}
            tickLine={false}
            width={42}
            domain={[0, Math.ceil(forecast.maxCapacityKw * 1.05)]}
          />
          <Tooltip
            contentStyle={TOOLTIP}
            labelStyle={{ color: AXIS }}
            formatter={(v) => [`${(v as number).toFixed(1)} kW`, "Predicted"]}
          />
          <ReferenceLine y={warningKw} stroke="#f59e0b" strokeDasharray="4 4" />
          <ReferenceLine y={criticalKw} stroke="#ef4444" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="load"
            stroke="#a78bfa"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={{ r: 2.5, fill: "#a78bfa" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
