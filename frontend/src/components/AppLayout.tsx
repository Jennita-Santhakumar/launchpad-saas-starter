import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useNavigate, useParams } from "react-router-dom";

import { listWorkspaces } from "../api/client";
import type { Workspace } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

export interface WorkspaceOutletContext {
  workspace: Workspace;
  workspaces: Workspace[];
  refreshWorkspaces: () => Promise<void>;
}

const NAV_ITEMS: { to: string; label: string; end: boolean }[] = [
  { to: "", label: "Dashboard", end: true },
  { to: "members", label: "Members", end: false },
  { to: "billing", label: "Billing", end: false },
  { to: "analytics", label: "Analytics", end: false },
];

export default function AppLayout() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshWorkspaces = useCallback(async () => {
    try {
      const list = await listWorkspaces();
      setWorkspaces(list);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshWorkspaces();
  }, [refreshWorkspaces]);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading workspace...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-red-600">
        Could not load workspaces ({error})
      </div>
    );
  }

  const workspace = workspaces.find((w) => w.id === workspaceId);

  if (!workspace) {
    return <Navigate to="/workspaces" replace />;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-4">
          <span className="text-lg font-semibold tracking-tight text-slate-900">Orbit</span>
        </div>
        <div className="border-b border-slate-200 px-4 py-3">
          <WorkspaceSwitcher
            workspaces={workspaces}
            currentWorkspaceId={workspace.id}
            onSelect={(id) => navigate(`/w/${id}`)}
            onCreateNew={() => navigate("/workspaces")}
          />
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.label}
              to={`/w/${workspace.id}${item.to ? `/${item.to}` : ""}`}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-4 py-3">
          <div className="truncate text-sm font-medium text-slate-900">{user?.name}</div>
          <div className="truncate text-xs text-slate-500">{user?.email}</div>
          <button
            onClick={handleLogout}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-slate-50 px-8 py-8">
        <Outlet
          context={
            { workspace, workspaces, refreshWorkspaces } satisfies WorkspaceOutletContext
          }
        />
      </main>
    </div>
  );
}
