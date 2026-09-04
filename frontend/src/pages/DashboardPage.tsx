import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { getAnalytics, getSubscription } from "../api/client";
import type { AnalyticsSummaryItem, Subscription } from "../api/types";
import type { WorkspaceOutletContext } from "../components/AppLayout";
import RoleBadge from "../components/RoleBadge";
import StatCard from "../components/StatCard";

export default function DashboardPage() {
  const { workspace } = useOutletContext<WorkspaceOutletContext>();
  const [summary, setSummary] = useState<AnalyticsSummaryItem[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([getAnalytics(workspace.id), getSubscription(workspace.id)])
      .then(([analytics, sub]) => {
        setSummary(analytics.summary);
        setSubscription(sub);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, [workspace.id]);

  const totalEvents = summary.reduce((sum, item) => sum + item.count, 0);

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{workspace.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-sm text-slate-500">Your role:</span>
            <RoleBadge role={workspace.role ?? "member"} />
          </div>
        </div>
      </div>

      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {isLoading && <p className="mt-6 text-sm text-slate-500">Loading...</p>}

      {!isLoading && !error && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Total events" value={String(totalEvents)} />
          <StatCard label="Event types tracked" value={String(summary.length)} />
          <StatCard
            label="Plan"
            value={subscription ? subscription.plan : "No plan"}
            hint={subscription ? subscription.status : "Visit Billing to subscribe"}
          />
        </div>
      )}

      {!isLoading && !error && summary.length > 0 && (
        <div className="mt-8 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-medium text-slate-700">Events by type</h2>
          <div className="mt-3 divide-y divide-slate-100">
            {summary.map((item) => (
              <div key={item.event_type} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-700">{item.event_type}</span>
                <span className="font-medium text-slate-900">{item.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isLoading && !error && summary.length === 0 && (
        <p className="mt-8 text-sm text-slate-500">
          No usage events recorded yet. Once your app starts sending events to{" "}
          <code className="rounded bg-slate-100 px-1">POST /workspaces/{workspace.id}/analytics/events</code>, they
          will show up here and on the Analytics page.
        </p>
      )}
    </div>
  );
}
