import { History, Plug, SlidersHorizontal } from "lucide-react";

import { CardHeading } from "@/components/CardHeading";
import { Card, CardContent } from "@/components/ui/card";
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
  LoadThresholdReached: "hsl(var(--warning))",
  LoadRuleActivated: "hsl(217 91% 60%)",
  ChargingPowerReduced: "hsl(199 89% 55%)",
  CurrentLoadUpdated: "hsl(var(--muted-foreground))",
  RegulationResultEvaluated: "hsl(258 80% 64%)",
  LoadAreaStabilized: "hsl(var(--stable))",
  RegulationFailed: "hsl(var(--critical))",
};

function eventDetail(event: RegulationEvent): string {
  const load = event.payload["current_load_kw"];
  return typeof load === "number" ? ` · ${load.toFixed(1)} kW` : "";
}

export function RegulationTimeline({ events }: { events: RegulationEvent[] }) {
  return (
    <Card>
      <CardHeading icon={<History className="h-4 w-4" />} color="hsl(258 80% 64%)" title="Regulation Events" />
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
                  style={{ backgroundColor: EVENT_COLOR[e.eventType] ?? "hsl(var(--muted-foreground))" }}
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

export function SessionsTable({ sessions, filter }: { sessions: Session[]; filter: string }) {
  const q = filter.trim().toLowerCase();
  const rows = q ? sessions.filter((s) => s.chargerId.toLowerCase().includes(q)) : sessions;
  return (
    <Card id="sessions">
      <CardHeading
        icon={<Plug className="h-4 w-4" />}
        color="hsl(217 91% 60%)"
        title="Active Charging Sessions"
        right={<span className="text-xs text-muted-foreground">{rows.length} shown</span>}
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
                  <TableRow key={s.sessionId}>
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
    </Card>
  );
}

export function AdjustmentsTable({ adjustments }: { adjustments: Adjustment[] }) {
  return (
    <Card>
      <CardHeading
        icon={<SlidersHorizontal className="h-4 w-4" />}
        color="hsl(142 66% 42%)"
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
