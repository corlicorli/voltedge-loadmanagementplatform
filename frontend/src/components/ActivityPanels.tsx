import { History, Plug, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { CardHeading } from "@/components/CardHeading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Adjustment, RegulationEvent, Session } from "@/lib/api";
import { fmtDateTime, fmtTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const EVENT_COLOR: Record<string, string> = {
  LoadThresholdReached: "hsl(0 0% 45%)",
  LoadRuleActivated: "hsl(0 0% 30%)",
  ChargingPowerReduced: "hsl(0 0% 55%)",
  CurrentLoadUpdated: "hsl(0 0% 72%)",
  RegulationResultEvaluated: "hsl(0 0% 35%)",
  LoadAreaStabilized: "hsl(0 0% 60%)",
  RegulationFailed: "hsl(0 0% 12%)",
};

function eventDetail(event: RegulationEvent): string {
  const load = event.payload["current_load_kw"];
  return typeof load === "number" ? ` · ${load.toFixed(1)} kW` : "";
}

export function RegulationTimeline({ events }: { events: RegulationEvent[] }) {
  return (
    <Card>
      <CardHeading icon={<History className="h-4 w-4" />} color="hsl(0 0% 16%)" title="Regulation Events" />
      <CardContent>
        {events.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No regulation events yet — start a session via Postman to trigger regulation.
          </p>
        ) : (
          <div className="max-h-[320px] overflow-y-auto pr-1">
            {events.map((e, i) => (
              <div
                key={`${e.eventType}-${e.occurredAt}-${i}`}
                className="flex items-start gap-3 border-b border-border/60 py-2.5 last:border-0"
              >
                <span
                  className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: EVENT_COLOR[e.eventType] ?? "hsl(0 0% 45%)" }}
                />
                <div className="flex-1">
                  <div className="text-sm font-medium">{e.eventType}</div>
                  <div className="text-xs text-muted-foreground">
                    {fmtDateTime(e.occurredAt)}
                    {eventDetail(e)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface SessionsTableProps {
  sessions: Session[];
  filter: string;
  adjustments: Adjustment[];
}

export function SessionsTable({ sessions, filter, adjustments }: SessionsTableProps) {
  const [selected, setSelected] = useState<Session | null>(null);
  const q = filter.trim().toLowerCase();
  const rows = q ? sessions.filter((s) => s.chargerId.toLowerCase().includes(q)) : sessions;
  const selectedAdjustments = selected
    ? adjustments.filter((a) => a.sessionId === selected.sessionId)
    : [];

  return (
    <Card id="sessions" className="scroll-mt-24">
      <CardHeading
        icon={<Plug className="h-4 w-4" />}
        color="hsl(0 0% 16%)"
        title="Active Charging Sessions"
        right={<span className="text-xs text-muted-foreground">{rows.length} shown · click a row</span>}
      />
      <CardContent>
        <div className="max-h-[320px] overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Charger</TableHead>
                <TableHead>Requested</TableHead>
                <TableHead>Current</TableHead>
                <TableHead>State</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((s) => {
                const reduced = s.currentPowerKw < s.requestedPowerKw;
                return (
                  <TableRow
                    key={s.sessionId}
                    onClick={() => setSelected(s)}
                    className="cursor-pointer"
                  >
                    <TableCell className="font-medium">{s.chargerId}</TableCell>
                    <TableCell>{s.requestedPowerKw.toFixed(1)} kW</TableCell>
                    <TableCell className={cn(reduced && "font-medium text-warning")}>
                      {s.currentPowerKw.toFixed(1)} kW
                    </TableCell>
                    <TableCell className="text-muted-foreground">{reduced ? "REDUCED" : "FULL"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent>
          {selected && <SessionDetail session={selected} adjustments={selectedAdjustments} />}
        </SheetContent>
      </Sheet>
    </Card>
  );
}

function SessionDetail({ session, adjustments }: { session: Session; adjustments: Adjustment[] }) {
  const reduced = session.currentPowerKw < session.requestedPowerKw;
  const reductionPct =
    session.requestedPowerKw > 0
      ? ((session.requestedPowerKw - session.currentPowerKw) / session.requestedPowerKw) * 100
      : 0;
  return (
    <>
      <SheetHeader>
        <SheetTitle>Charger {session.chargerId}</SheetTitle>
        <SheetDescription>Charging session detail</SheetDescription>
      </SheetHeader>
      <div className="mt-6 space-y-6">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{session.status}</Badge>
          <Badge variant={reduced ? "warning" : "stable"}>{reduced ? "REDUCED" : "FULL POWER"}</Badge>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-4">
          <Field label="Requested power" value={`${session.requestedPowerKw.toFixed(1)} kW`} />
          <Field label="Current power" value={`${session.currentPowerKw.toFixed(1)} kW`} />
          <Field label="Reduction" value={reduced ? `${reductionPct.toFixed(0)}%` : "—"} />
          <Field label="Started" value={fmtDateTime(session.startedAt)} />
          <Field label="Duration" value={duration(session.startedAt)} />
        </dl>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Session ID
          </div>
          <div className="mt-1 break-all font-mono text-xs">{session.sessionId}</div>
        </div>
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Adjustment history ({adjustments.length})
          </div>
          {adjustments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No adjustments for this session.</p>
          ) : (
            <div className="space-y-2">
              {adjustments.map((a) => (
                <div key={a.adjustmentId} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium tabular-nums">
                      {a.previousPowerKw.toFixed(1)} → {a.newPowerKw.toFixed(1)} kW
                    </span>
                    <span className="text-xs text-muted-foreground">{fmtTime(a.createdAt)}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{a.reason}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

function duration(startIso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(startIso).getTime()) / 60000));
  if (mins < 60) return `${mins} min`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export function AdjustmentsTable({ adjustments }: { adjustments: Adjustment[] }) {
  return (
    <Card>
      <CardHeading
        icon={<SlidersHorizontal className="h-4 w-4" />}
        color="hsl(0 0% 16%)"
        title="Load Adjustments"
        right={<span className="text-xs text-muted-foreground">{adjustments.length} recent</span>}
      />
      <CardContent>
        {adjustments.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">No load adjustments yet.</p>
        ) : (
          <div className="max-h-[320px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Session</TableHead>
                  <TableHead>Change</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {adjustments.map((a) => (
                  <TableRow key={a.adjustmentId}>
                    <TableCell>{fmtTime(a.createdAt)}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {a.sessionId.slice(0, 8)}
                    </TableCell>
                    <TableCell>
                      {a.previousPowerKw.toFixed(1)} → {a.newPowerKw.toFixed(1)} kW
                    </TableCell>
                    <TableCell className="text-muted-foreground">{a.reason}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
