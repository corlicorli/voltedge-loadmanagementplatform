import type { CSSProperties } from "react";

import type { AreaStatus, Kpis } from "../lib/api";
import { STATUS_COLOR, fmtKw } from "../lib/format";

interface Props {
  status: AreaStatus;
  kpis: Kpis | null;
}

export function KpiCards({ status, kpis }: Props) {
  const util = kpis?.currentUtilisationPct ?? (status.currentLoadKw / status.maxCapacityKw) * 100;
  const gaugeStyle = {
    "--pct": Math.min(util, 100),
    "--ring": STATUS_COLOR[status.status],
  } as CSSProperties;

  return (
    <div className="kpi-grid">
      <div className="kpi gauge-card">
        <div className="gauge" style={gaugeStyle}>
          <div style={{ textAlign: "center" }}>
            <div className="g-val">{util.toFixed(0)}%</div>
            <div className="g-unit">load</div>
          </div>
        </div>
        <div>
          <div className="label">Current load</div>
          <div className="value">
            {status.currentLoadKw.toFixed(1)}
            <small> / {status.maxCapacityKw.toFixed(0)} kW</small>
          </div>
          <div style={{ marginTop: 10 }}>
            <span className={`badge ${status.status}`}>{status.status}</span>
          </div>
        </div>
      </div>

      <Kpi label="Available capacity" value={fmtKw(status.availableCapacityKw)} />
      <Kpi label="Active sessions" value={`${status.activeSessionCount}`} />
      <Kpi label="Peak load · 24h" value={fmtKw(kpis?.peakLoad24HKw ?? null)} />
      <Kpi
        label="Open interventions"
        value={`${kpis?.openInterventions ?? 0}`}
        accent={kpis && kpis.openInterventions > 0 ? "var(--critical)" : undefined}
      />
    </div>
  );
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
    </div>
  );
}
