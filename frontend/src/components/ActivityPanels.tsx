import type { Adjustment, RegulationEvent, Session } from "../lib/api";
import { fmtDateTime, fmtTime } from "../lib/format";

const EVENT_COLOR: Record<string, string> = {
  LoadThresholdReached: "#f59e0b",
  LoadRuleActivated: "#22d3ee",
  ChargingPowerReduced: "#38bdf8",
  CurrentLoadUpdated: "#64748b",
  RegulationResultEvaluated: "#a78bfa",
  LoadAreaStabilized: "#22c55e",
  RegulationFailed: "#ef4444",
};

function eventDetail(event: RegulationEvent): string {
  const load = event.payload["current_load_kw"];
  return typeof load === "number" ? ` · ${load.toFixed(1)} kW` : "";
}

export function RegulationTimeline({ events }: { events: RegulationEvent[] }) {
  return (
    <div className="card">
      <h2>
        Regulation events <span className="hint">diagnostic · latest</span>
      </h2>
      {events.length === 0 ? (
        <div className="empty">No regulation events yet — start a session via Postman to trigger regulation.</div>
      ) : (
        <div className="timeline">
          {events.map((e, i) => (
            <div className="tl-item" key={`${e.eventType}-${e.occurredAt}-${i}`}>
              <span className="tl-dot" style={{ background: EVENT_COLOR[e.eventType] ?? "#8a98b5" }} />
              <div className="tl-body">
                <div className="tl-type">{e.eventType}</div>
                <div className="tl-meta">
                  {fmtDateTime(e.occurredAt)}
                  {eventDetail(e)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function SessionsTable({ sessions }: { sessions: Session[] }) {
  return (
    <div className="card">
      <h2>
        Active charging sessions <span className="hint">{sessions.length} active</span>
      </h2>
      <div className="scroll">
        <table className="table">
          <thead>
            <tr>
              <th>Charger</th>
              <th>Requested</th>
              <th>Current</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => {
              const reduced = s.currentPowerKw < s.requestedPowerKw;
              return (
                <tr key={s.sessionId}>
                  <td>{s.chargerId}</td>
                  <td>{s.requestedPowerKw.toFixed(1)} kW</td>
                  <td style={{ color: reduced ? "#f59e0b" : undefined }}>
                    {s.currentPowerKw.toFixed(1)} kW
                  </td>
                  <td>{reduced ? "REDUCED" : "FULL"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AdjustmentsTable({ adjustments }: { adjustments: Adjustment[] }) {
  return (
    <div className="card">
      <h2>
        Load adjustments <span className="hint">{adjustments.length} most recent</span>
      </h2>
      {adjustments.length === 0 ? (
        <div className="empty">No load adjustments yet.</div>
      ) : (
        <div className="scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Session</th>
                <th>Change</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {adjustments.map((a) => (
                <tr key={a.adjustmentId}>
                  <td>{fmtTime(a.createdAt)}</td>
                  <td className="mono">{a.sessionId.slice(0, 8)}</td>
                  <td>
                    {a.previousPowerKw.toFixed(1)} → {a.newPowerKw.toFixed(1)} kW
                  </td>
                  <td className="muted">{a.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
