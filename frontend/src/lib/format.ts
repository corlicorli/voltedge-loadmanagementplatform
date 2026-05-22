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

// Danish / European formatting: 24-hour clock, DD. month, da-DK locale.
const LOCALE = "da-DK";

export const fmtKw = (n: number | null | undefined): string =>
  n == null ? "—" : `${n.toFixed(1)} kW`;

export const fmtTime = (iso: string): string =>
  new Date(iso).toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });

export const fmtDateTime = (iso: string): string =>
  new Date(iso).toLocaleString(LOCALE, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

export const fmtDay = (iso: string): string =>
  new Date(iso).toLocaleDateString(LOCALE, { weekday: "short", day: "numeric" });

export const fmtClock = (d: Date): string =>
  d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
