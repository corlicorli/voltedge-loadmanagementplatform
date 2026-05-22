import { Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AdjustmentsTable, RegulationTimeline, SessionsTable } from "@/components/ActivityPanels";
import { KpiCards } from "@/components/KpiCards";
import { LoadTrendChart } from "@/components/LoadCharts";
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
import { cn } from "@/lib/utils";

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

  return (
    <div className="mx-auto max-w-[1360px] px-6 py-6 lg:px-8">
      <Header updatedAt={updatedAt} areaName={data?.status.areaName} areaCode={data?.status.areaCode} />
      {error && !data ? (
        <ErrorState message={error} />
      ) : !data ? (
        <LoadingState />
      ) : (
        <div className="space-y-4">
          <KpiCards status={data.status} kpis={data.kpis} />
          <LoadTrendChart
            data={data.timeseries}
            warningKw={data.status.warningThresholdKw}
            criticalKw={data.status.criticalThresholdKw}
            maxKw={data.status.maxCapacityKw}
          />
          <div className="grid gap-4 lg:grid-cols-2">
            <DailyPeaksChart
              data={data.dailyPeaks}
              warningKw={data.status.warningThresholdKw}
              criticalKw={data.status.criticalThresholdKw}
              maxKw={data.status.maxCapacityKw}
            />
            <StatusDonut data={data.distribution} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <RegulationTimeline events={data.events} />
            <SessionsTable sessions={data.sessions} />
          </div>
          <AdjustmentsTable adjustments={data.adjustments} />
        </div>
      )}
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
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
      <div className="flex items-center gap-3.5">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-primary to-sky-600 text-primary-foreground shadow-lg shadow-primary/30">
          <Zap className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight">VoltEdge · Load Management BI</h1>
          <p className="text-[13px] text-muted-foreground">
            {areaName ? `${areaName} (${areaCode})` : "Load Control Context"} · Business Intelligence Dashboard
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-[13px] text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-stable opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-stable" />
          </span>
          Live · {POLL_MS / 1000}s
        </span>
        {updatedAt && <span>Updated {updatedAt.toLocaleTimeString()}</span>}
      </div>
    </header>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className={cn("h-[118px]", i === 0 && "lg:col-span-2")} />
        ))}
      </div>
      <Skeleton className="h-[320px]" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[300px]" />
        <Skeleton className="h-[300px]" />
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
