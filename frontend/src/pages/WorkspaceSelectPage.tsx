import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { createWorkspace, listWorkspaces } from "../api/client";
import type { Workspace } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import RoleBadge from "../components/RoleBadge";

export default function WorkspaceSelectPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    listWorkspaces()
      .then(setWorkspaces)
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      const workspace = await createWorkspace(newName.trim());
      navigate(`/w/${workspace.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Choose a workspace</h1>
            <p className="mt-1 text-sm text-slate-500">Signed in as {user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>

        {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {isLoading ? (
          <p className="mt-6 text-sm text-slate-500">Loading...</p>
        ) : (
          <div className="mt-6 space-y-2">
            {workspaces.map((w) => (
              <button
                key={w.id}
                onClick={() => navigate(`/w/${w.id}`)}
                className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-left hover:border-slate-300 hover:shadow-sm"
              >
                <span className="text-sm font-medium text-slate-900">{w.name}</span>
                <RoleBadge role={w.role ?? "member"} />
              </button>
            ))}
            {workspaces.length === 0 && (
              <p className="text-sm text-slate-500">
                You are not a member of any workspace yet. Create one below.
              </p>
            )}
          </div>
        )}

        <form onSubmit={handleCreate} className="mt-8 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-medium text-slate-700">Create a new workspace</h2>
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              placeholder="Workspace name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isCreating}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {isCreating ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
