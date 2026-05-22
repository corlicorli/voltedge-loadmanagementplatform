import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  LoadRuleActivated: "hsl(var(--primary))",
  ChargingPowerReduced: "hsl(199 89% 62%)",
  CurrentLoadUpdated: "hsl(var(--muted-foreground))",
  RegulationResultEvaluated: "hsl(258 90% 66%)",
  LoadAreaStabilized: "hsl(var(--stable))",
  RegulationFailed: "hsl(var(--critical))",
};

const TITLE = "text-xs font-medium uppercase tracking-wide text-muted-foreground";

function eventDetail(event: RegulationEvent): string {
  const load = event.payload["current_load_kw"];
  return typeof load === "number" ? ` · ${load.toFixed(1)} kW` : "";
}

export function RegulationTimeline({ events }: { events: RegulationEvent[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className={TITLE}>
          Regulation events <span className="font-normal normal-case">· diagnostic</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No regulation events yet — start a session via Postman to trigger regulation.
          </p>
        ) : (
          <div className="max-h-[300px] overflow-y-auto pr-1">
            {events.map((e, i) => (
              <div
                key={`${e.eventType}-${e.occurredAt}-${i}`}
                className="flex items-start gap-3 border-b border-border/50 py-2.5 last:border-0"
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

export function SessionsTable({ sessions }: { sessions: Session[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className={TITLE}>
          Active charging sessions <span className="font-normal normal-case">· {sessions.length} active</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-[300px] overflow-y-auto">
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
              {sessions.map((s) => {
                const reduced = s.currentPowerKw < s.requestedPowerKw;
                return (
                  <TableRow key={s.sessionId}>
                    <TableCell className="font-medium">{s.chargerId}</TableCell>
                    <TableCell>{s.requestedPowerKw.toFixed(1)} kW</TableCell>
                    <TableCell className={cn(reduced && "text-warning")}>
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
      <CardHeader className="pb-2">
        <CardTitle className={TITLE}>
          Load adjustments <span className="font-normal normal-case">· {adjustments.length} most recent</span>
        </CardTitle>
      </CardHeader>
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
