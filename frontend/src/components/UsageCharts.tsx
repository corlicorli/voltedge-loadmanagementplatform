import type { CSSProperties } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DailyPeak, LoadStatus, StatusDistribution } from "../lib/api";
import { STATUS_COLOR, fmtDay } from "../lib/format";

const AXIS = "#8a98b5";
const GRID = "#243049";
const TOOLTIP: CSSProperties = {
  background: "#1a2236",
  border: "1px solid #243049",
  borderRadius: 10,
  fontSize: 12,
  color: "#e7ecf5",
};

interface PeaksProps {
  data: DailyPeak[];
  warningKw: number;
  criticalKw: number;
  maxKw: number;
}

export function DailyPeaksChart({ data, warningKw, criticalKw, maxKw }: PeaksProps) {
  const rows = data.map((d) => ({ day: fmtDay(d.day), peak: d.peakLoadKw, avg: d.avgLoadKw }));
  const colorFor = (peak: number) =>
    peak >= criticalKw ? STATUS_COLOR.CRITICAL : peak >= warningKw ? STATUS_COLOR.WARNING : STATUS_COLOR.STABLE;
  return (
    <div className="card">
      <h2>
        Daily peak load <span className="hint">last 7 days · kW</span>
      </h2>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" stroke={AXIS} fontSize={11} tickLine={false} />
          <YAxis stroke={AXIS} fontSize={11} tickLine={false} width={42} domain={[0, Math.ceil(maxKw * 1.05)]} />
          <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: AXIS }} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine y={criticalKw} stroke="#ef4444" strokeDasharray="4 4" />
          <Bar dataKey="avg" name="Avg" fill="#334155" radius={[3, 3, 0, 0]} maxBarSize={26} />
          <Bar dataKey="peak" name="Peak" radius={[3, 3, 0, 0]} maxBarSize={26}>
            {rows.map((r) => (
              <Cell key={r.day} fill={colorFor(r.peak)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StatusDonut({ data }: { data: StatusDistribution[] }) {
  const rows = data.map((d) => ({ name: d.status as LoadStatus, value: d.samples }));
  return (
    <div className="card">
      <h2>
        Status distribution <span className="hint">last 7 days</span>
      </h2>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            innerRadius={62}
            outerRadius={94}
            paddingAngle={2}
            stroke="none"
          >
            {rows.map((r) => (
              <Cell key={r.name} fill={STATUS_COLOR[r.name]} />
            ))}
          </Pie>
          <Tooltip contentStyle={TOOLTIP} formatter={(value, name) => [`${value} samples`, name as string]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
