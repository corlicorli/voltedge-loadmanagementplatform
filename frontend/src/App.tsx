import { useCallback, useEffect, useState } from "react";

import { AdjustmentsTable, RegulationTimeline, SessionsTable } from "./components/ActivityPanels";
import { KpiCards } from "./components/KpiCards";
import { ForecastChart, LoadTrendChart } from "./components/LoadCharts";
import { DailyPeaksChart, StatusDonut } from "./components/UsageCharts";
import {
  api,
  type Adjustment,
  type AreaStatus,
  type DailyPeak,
  type Forecast,
  type Kpis,
  type LoadSample,
  type RegulationEvent,
  type Session,
  type StatusDistribution,
} from "./lib/api";

const AREA = "YN";
const POLL_MS = 5000;

interface DashboardData {
  status: AreaStatus;
  kpis: Kpis;
  timeseries: LoadSample[];
  dailyPeaks: DailyPeak[];
  distribution: StatusDistribution[];
  events: RegulationEvent[];
  forecast: Forecast;
  sessions: Session[];
  adjustments: Adjustment[];
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [status, kpis, timeseries, dailyPeaks, distribution, events, forecast, sessions, adjustments] =
        await Promise.all([
          api.status(AREA),
          api.kpis(AREA),
          api.timeseries(AREA, 24),
          api.dailyPeaks(AREA, 7),
          api.statusDistribution(AREA, 7),
          api.regulationEvents(AREA, 15),
          api.forecast(AREA, 12),
          api.sessions(AREA),
          api.adjustments(AREA),
        ]);
      setData({ status, kpis, timeseries, dailyPeaks, distribution, events, forecast, sessions, adjustments });
      setError(null);
      setUpdatedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  if (error && !data) {
    return (
      <div className="app">
        <Header updatedAt={null} />
        <div className="center-screen">
          <div className="error-box">
            <b>Cannot reach the Load Control Service</b>
            <div style={{ marginTop: 8, fontSize: 13 }}>{error}</div>
            <div style={{ marginTop: 8, fontSize: 12 }} className="muted">
              Expected API at {api.baseUrl}. Is the backend running?
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app">
        <Header updatedAt={null} />
        <div className="center-screen">
          <div>
            <div className="spinner" />
            <div className="muted" style={{ marginTop: 12 }}>
              Loading load-management data…
            </div>
          </div>
        </div>
      </div>
    );
  }

  const s = data.status;
  return (
    <div className="app">
      <Header updatedAt={updatedAt} areaName={s.areaName} areaCode={s.areaCode} />
      <KpiCards status={s} kpis={data.kpis} />

      <div className="grid cols-2" style={{ marginBottom: 18 }}>
        <LoadTrendChart
          data={data.timeseries}
          warningKw={s.warningThresholdKw}
          criticalKw={s.criticalThresholdKw}
          maxKw={s.maxCapacityKw}
        />
        <ForecastChart
          forecast={data.forecast}
          warningKw={s.warningThresholdKw}
          criticalKw={s.criticalThresholdKw}
        />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 18 }}>
        <DailyPeaksChart
          data={data.dailyPeaks}
          warningKw={s.warningThresholdKw}
          criticalKw={s.criticalThresholdKw}
          maxKw={s.maxCapacityKw}
        />
        <StatusDonut data={data.distribution} />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 18 }}>
        <RegulationTimeline events={data.events} />
        <SessionsTable sessions={data.sessions} />
      </div>

      <AdjustmentsTable adjustments={data.adjustments} />
    </div>
  );
}

function Header({
  updatedAt,
  areaName,
  areaCode,
}: {
  updatedAt: Date | null;
  areaName?: string;
  areaCode?: string;
}) {
  return (
    <div className="header">
      <div className="brand">
        <div className="bolt">⚡</div>
        <div>
          <h1>VoltEdge · Load Management BI</h1>
          <div className="sub">
            {areaName ? `${areaName} (${areaCode})` : "Load Control Context"} · Business Intelligence Dashboard
          </div>
        </div>
      </div>
      <div className="header-meta">
        <span>
          <span className="live-dot" />
          Live · refresh {POLL_MS / 1000}s
        </span>
        {updatedAt && <span>Updated {updatedAt.toLocaleTimeString()}</span>}
      </div>
    </div>
  );
}
