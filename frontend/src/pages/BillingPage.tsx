import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { getSubscription, openBillingPortal, subscribe } from "../api/client";
import type { Subscription } from "../api/types";
import type { WorkspaceOutletContext } from "../components/AppLayout";

const PLANS: { id: string; name: string; price: string; blurb: string }[] = [
  { id: "free", name: "Free", price: "$0/mo", blurb: "For personal projects and evaluation." },
  { id: "starter", name: "Starter", price: "$19/mo", blurb: "For small teams getting started." },
  { id: "pro", name: "Pro", price: "$49/mo", blurb: "For growing teams that need more." },
  { id: "enterprise", name: "Enterprise", price: "Contact us", blurb: "For large organizations." },
];

export default function BillingPage() {
  const { workspace } = useOutletContext<WorkspaceOutletContext>();
  const canManage = workspace.role === "owner" || workspace.role === "admin";

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [portalBusy, setPortalBusy] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);

  const load = useCallback(() => {
    setIsLoading(true);
    getSubscription(workspace.id)
      .then(setSubscription)
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, [workspace.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubscribe(plan: string) {
    setBusyPlan(plan);
    setError(null);
    try {
      const sub = await subscribe(workspace.id, plan);
      setSubscription(sub);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusyPlan(null);
    }
  }

  async function handlePortal() {
    setPortalBusy(true);
    setError(null);
    try {
      const { url } = await openBillingPortal(workspace.id);
      setPortalUrl(url);
    } catch (err) {
      setError(String(err));
    } finally {
      setPortalBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Billing</h1>

      <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        <strong>Mock billing mode:</strong> no real payment provider is connected. Subscribing and
        the billing portal use an in-memory mock of Stripe for demonstration purposes -- no card
        details are collected and no real charges occur.
      </div>

      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {isLoading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : (
        <>
          <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-medium text-slate-700">Current plan</h2>
            {subscription ? (
              <div className="mt-2">
                <div className="text-2xl font-semibold capitalize text-slate-900">{subscription.plan}</div>
                <div className="mt-1 text-sm text-slate-500">
                  Status: <span className="font-medium capitalize">{subscription.status}</span>
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  Current period: {new Date(subscription.current_period_start).toLocaleDateString()}{" "}
                  - {new Date(subscription.current_period_end).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No active subscription yet.</p>
            )}

            {canManage && subscription && (
              <button
                onClick={handlePortal}
                disabled={portalBusy}
                className="mt-4 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                {portalBusy ? "Opening..." : "Manage billing"}
              </button>
            )}
            {portalUrl && (
              <p className="mt-2 text-xs text-slate-500">
                Mock portal session:{" "}
                <a href={portalUrl} target="_blank" rel="noreferrer" className="text-slate-900 underline">
                  {portalUrl}
                </a>
              </p>
            )}
          </div>

          {canManage ? (
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {PLANS.map((plan) => {
                const isCurrent = subscription?.plan === plan.id;
                return (
                  <div key={plan.id} className="flex flex-col rounded-lg border border-slate-200 bg-white p-4">
                    <div className="text-sm font-semibold text-slate-900">{plan.name}</div>
                    <div className="mt-1 text-lg font-semibold text-slate-900">{plan.price}</div>
                    <p className="mt-2 flex-1 text-xs text-slate-500">{plan.blurb}</p>
                    <button
                      onClick={() => handleSubscribe(plan.id)}
                      disabled={isCurrent || busyPlan === plan.id}
                      className="mt-4 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                    >
                      {isCurrent ? "Current plan" : busyPlan === plan.id ? "Updating..." : "Choose plan"}
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-6 text-sm text-slate-500">Only owners and admins can change the plan.</p>
          )}
        </>
      )}
    </div>
  );
}
