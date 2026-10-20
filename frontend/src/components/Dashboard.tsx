import { useCallback, useEffect, useState } from "react";
import { api, Stats, Ticket, Trace } from "../api";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, tr, tk] = await Promise.all([api.stats(), api.traces(100), api.tickets(50)]);
      setStats(s);
      setTraces(tr);
      setTickets(tk);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="dash">
      <div className="dash-head">
        <h2>Operations dashboard</h2>
        <button onClick={() => void load()}>Refresh</button>
      </div>
      {error && <div className="error">{error}</div>}
      {stats && (
        <div className="cards">
          <div className="card"><b>{stats.total}</b><span>Conversations</span></div>
          <div className="card"><b>{stats.auto_answered}</b><span>Auto-answered</span></div>
          <div className="card"><b>{stats.escalated}</b><span>Escalated</span></div>
          <div className="card"><b>{(stats.auto_rate * 100).toFixed(0)}%</b><span>Auto rate</span></div>
          <div className="card"><b>{stats.avg_latency_ms.toFixed(0)} ms</b><span>Avg latency</span></div>
        </div>
      )}
      {stats && stats.top_escalation_reasons.length > 0 && (
        <>
          <h4>Top escalation reasons</h4>
          <ul className="reasons">
            {stats.top_escalation_reasons.map((r) => (
              <li key={r.reason}>
                <span className="mono">{r.reason}</span> <b>{r.count}</b>
              </li>
            ))}
          </ul>
        </>
      )}
      <h4>Recent traces</h4>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Message</th><th>Intent</th><th>Action</th><th>Conf</th><th>Reason</th><th>Latency</th></tr>
          </thead>
          <tbody>
            {traces.map((t) => (
              <tr key={t.id} className={t.action === "ESCALATE" ? "esc" : ""}>
                <td>{t.id}</td>
                <td>{t.message.slice(0, 70)}</td>
                <td>{t.intent}</td>
                <td>{t.action}</td>
                <td>{t.confidence.toFixed(2)}</td>
                <td className="mono">{t.reason ?? ""}</td>
                <td>{t.latency_ms.toFixed(0)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4>Open tickets for humans</h4>
      {tickets.length === 0 ? (
        <p className="muted">No tickets yet.</p>
      ) : (
        <ul className="tickets">
          {tickets.map((t) => (
            <li key={t.id}>
              <b>#{t.id}</b> <span className="badge warn small">{t.reason}</span> {t.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
