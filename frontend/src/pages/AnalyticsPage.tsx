import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAnalytics } from "../api/client";
import type { AnalyticsSummaryItem, AnalyticsTimeseriesPoint } from "../api/types";
import type { WorkspaceOutletContext } from "../components/AppLayout";

export default function AnalyticsPage() {
  const { workspace } = useOutletContext<WorkspaceOutletContext>();
  const [timeseries, setTimeseries] = useState<AnalyticsTimeseriesPoint[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummaryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    getAnalytics(workspace.id)
      .then(({ timeseries: ts, summary: sum }) => {
        setTimeseries(ts);
        setSummary(sum);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, [workspace.id]);

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Analytics</h1>
      <p className="mt-1 text-sm text-slate-500">Usage events ingested for {workspace.name}.</p>

      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {isLoading && <p className="mt-6 text-sm text-slate-500">Loading...</p>}

      {!isLoading && !error && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-medium text-slate-700">Events over time</h2>
            {timeseries.length === 0 ? (
              <p className="mt-4 text-sm text-slate-500">No events recorded yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={timeseries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#2563eb" name="events" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-medium text-slate-700">Breakdown by event type</h2>
            {summary.length === 0 ? (
              <p className="mt-4 text-sm text-slate-500">No events recorded yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={summary}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="event_type" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#16a34a" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
