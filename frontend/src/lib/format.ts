import type { LoadStatus } from "./api";

export const STATUS_COLOR: Record<LoadStatus, string> = {
  STABLE: "#22c55e",
  WARNING: "#f59e0b",
  CRITICAL: "#ef4444",
};

export const fmtKw = (n: number | null | undefined): string =>
  n == null ? "—" : `${n.toFixed(1)} kW`;

export const fmtPct = (n: number | null | undefined): string =>
  n == null ? "—" : `${n.toFixed(1)}%`;

export const fmtTime = (iso: string): string =>
  new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export const fmtDateTime = (iso: string): string =>
  new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

export const fmtDay = (iso: string): string =>
  new Date(iso).toLocaleDateString([], { weekday: "short", day: "numeric" });
