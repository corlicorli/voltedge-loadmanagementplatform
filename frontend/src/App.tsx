import { useCallback, useEffect, useRef, useState } from "react";

import { AdjustmentsTable, RegulationTimeline, SessionsTable } from "@/components/ActivityPanels";
import { KpiCards } from "@/components/KpiCards";
import { LoadTrendChart } from "@/components/LoadCharts";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { DailyPeaksChart, StatusDonut } from "@/components/UsageCharts";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type Adjustment,
  type AreaStatus,
  type DailyPeak,
  type Kpis,
  type LoadSample,
  type RegulationEvent,
  type Session,
  type StatusDistribution,
  api,
} from "@/lib/api";
import { fmtClock } from "@/lib/format";

const AREA = "YN";
const POLL_MS = 5000;

interface DashboardData {
  status: AreaStatus;
  kpis: Kpis;
  timeseries: LoadSample[];
  dailyPeaks: DailyPeak[];
  distribution: StatusDistribution[];
  events: RegulationEvent[];
  sessions: Session[];
  adjustments: Adjustment[];
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    try {
      const [status, kpis, timeseries, dailyPeaks, distribution, events, sessions, adjustments] =
        await Promise.all([
          api.status(AREA),
          api.kpis(AREA),
          api.timeseries(AREA, 24),
          api.dailyPeaks(AREA, 7),
          api.statusDistribution(AREA, 7),
          api.regulationEvents(AREA, 15),
          api.sessions(AREA),
          api.adjustments(AREA),
        ]);
      setData({ status, kpis, timeseries, dailyPeaks, distribution, events, sessions, adjustments });
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

  // When a search starts, jump to the (filtered) sessions table so the effect is visible.
  const prevQuery = useRef("");
  useEffect(() => {
    if (prevQuery.current === "" && query !== "") {
      document.getElementById("sessions")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    prevQuery.current = query;
  }, [query]);

  const interventions = data?.kpis.openInterventions ?? 0;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          query={query}
          onQuery={setQuery}
          updatedLabel={updatedAt ? fmtClock(updatedAt) : null}
          onRefresh={load}
        />
        <main className="flex-1 p-4 lg:p-6">
          {error && !data ? (
            <ErrorState message={error} />
          ) : !data ? (
            <LoadingState />
          ) : (
            <div className="space-y-4">
              <div className="mb-1 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
                  <p className="text-sm text-muted-foreground">
                    {data.status.areaName} ({data.status.areaCode}) · Load Control Context
                  </p>
                </div>
                {interventions > 0 && (
                  <span className="rounded-full bg-critical/10 px-3 py-1.5 text-sm font-medium text-critical">
                    {interventions} open intervention{interventions > 1 ? "s" : ""}
                  </span>
                )}
              </div>

              <KpiCards status={data.status} kpis={data.kpis} series={data.timeseries} />

              <div className="grid gap-4 lg:grid-cols-3">
                <div id="analytics" className="scroll-mt-24 lg:col-span-2">
                  <LoadTrendChart
                    data={data.timeseries}
                    warningKw={data.status.warningThresholdKw}
                    criticalKw={data.status.criticalThresholdKw}
                    maxKw={data.status.maxCapacityKw}
                  />
                </div>
                <StatusDonut data={data.distribution} />
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <DailyPeaksChart
                    data={data.dailyPeaks}
                    warningKw={data.status.warningThresholdKw}
                    criticalKw={data.status.criticalThresholdKw}
                    maxKw={data.status.maxCapacityKw}
                  />
                </div>
                <RegulationTimeline events={data.events} />
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <SessionsTable sessions={data.sessions} filter={query} />
                <AdjustmentsTable adjustments={data.adjustments} />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[150px] rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-[340px] rounded-2xl lg:col-span-2" />
        <Skeleton className="h-[340px] rounded-2xl" />
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <Card className="mx-auto mt-16 max-w-lg border-critical/40">
      <CardContent className="p-6">
        <div className="font-semibold text-critical">Cannot reach the Load Control Service</div>
        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          Expected API at {api.baseUrl}. Is the backend running?
        </p>
      </CardContent>
    </Card>
  );
}
