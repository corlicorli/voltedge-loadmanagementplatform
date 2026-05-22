import type { LoadStatus } from "./api";

export const STATUS_COLOR: Record<LoadStatus, string> = {
  STABLE: "hsl(var(--stable))",
  WARNING: "hsl(var(--warning))",
  CRITICAL: "hsl(var(--critical))",
};

export const STATUS_BADGE: Record<LoadStatus, "stable" | "warning" | "critical"> = {
  STABLE: "stable",
  WARNING: "warning",
  CRITICAL: "critical",
};

export const fmtKw = (n: number | null | undefined): string =>
  n == null ? "—" : `${n.toFixed(1)} kW`;

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
