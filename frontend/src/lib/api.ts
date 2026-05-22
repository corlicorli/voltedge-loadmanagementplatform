// Typed client for the Load Control + Analytics REST APIs.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type LoadStatus = "STABLE" | "WARNING" | "CRITICAL";

export interface AreaStatus {
  areaCode: string;
  areaName: string;
  currentLoadKw: number;
  maxCapacityKw: number;
  warningThresholdKw: number;
  criticalThresholdKw: number;
  availableCapacityKw: number;
  status: LoadStatus;
  activeSessionCount: number;
  updatedAt: string;
}

export interface Kpis {
  areaCode: string;
  areaName: string;
  currentLoadKw: number;
  maxCapacityKw: number;
  availableCapacityKw: number;
  status: LoadStatus;
  activeSessionCount: number;
  currentUtilisationPct: number;
  peakLoad24HKw: number | null;
  totalAdjustments: number;
  openInterventions: number;
}

export interface LoadSample {
  sampledAt: string;
  currentLoadKw: number;
  availableCapacityKw: number;
  status: LoadStatus;
  activeSessionCount: number;
}

export interface DailyPeak {
  day: string;
  peakLoadKw: number;
  avgLoadKw: number;
  peakUtilisationPct: number;
  criticalSamples: number;
  warningSamples: number;
  stableSamples: number;
}

export interface StatusDistribution {
  status: LoadStatus;
  samples: number;
  pct: number;
}

export interface RegulationEvent {
  eventType: string;
  occurredAt: string;
  payload: Record<string, unknown>;
}

export interface Session {
  sessionId: string;
  chargerId: string;
  requestedPowerKw: number;
  currentPowerKw: number;
  status: string;
  startedAt: string;
}

export interface Adjustment {
  adjustmentId: string;
  sessionId: string;
  previousPowerKw: number;
  newPowerKw: number;
  reason: string;
  createdAt: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return (await res.json()) as T;
}

export const api = {
  baseUrl: BASE,
  status: (area: string) => get<AreaStatus>(`/load-areas/${area}/status`),
  sessions: (area: string) => get<Session[]>(`/load-areas/${area}/sessions`),
  adjustments: (area: string) => get<Adjustment[]>(`/load-areas/${area}/adjustments?limit=50`),
  kpis: (area: string) => get<Kpis>(`/analytics/${area}/kpis`),
  timeseries: (area: string, hours = 24) =>
    get<LoadSample[]>(`/analytics/${area}/load-timeseries?hours=${hours}`),
  dailyPeaks: (area: string, days = 7) =>
    get<DailyPeak[]>(`/analytics/${area}/daily-peaks?days=${days}`),
  statusDistribution: (area: string, days = 7) =>
    get<StatusDistribution[]>(`/analytics/${area}/status-distribution?days=${days}`),
  regulationEvents: (area: string, limit = 15) =>
    get<RegulationEvent[]>(`/analytics/${area}/regulation-events?limit=${limit}`),
};
