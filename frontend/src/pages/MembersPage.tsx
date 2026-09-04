import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useOutletContext } from "react-router-dom";

import { inviteMember, listMembers, removeMember, updateMemberRole } from "../api/client";
import type { WorkspaceMember, WorkspaceRole } from "../api/types";
import type { WorkspaceOutletContext } from "../components/AppLayout";
import RoleBadge from "../components/RoleBadge";

const ASSIGNABLE_ROLES: WorkspaceRole[] = ["owner", "admin", "member"];

export default function MembersPage() {
  const { workspace } = useOutletContext<WorkspaceOutletContext>();
  const canManage = workspace.role === "owner" || workspace.role === "admin";

  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<WorkspaceRole>("member");
  const [isInviting, setIsInviting] = useState(false);

  const load = useCallback(() => {
    setIsLoading(true);
    listMembers(workspace.id)
      .then(setMembers)
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, [workspace.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleInvite(e: FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setIsInviting(true);
    setError(null);
    try {
      await inviteMember(workspace.id, inviteEmail.trim(), inviteRole);
      setInviteEmail("");
      setInviteRole("member");
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setIsInviting(false);
    }
  }

  async function handleRoleChange(memberId: string, role: WorkspaceRole) {
    setError(null);
    try {
      await updateMemberRole(workspace.id, memberId, role);
      load();
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleRemove(memberId: string) {
    setError(null);
    try {
      await removeMember(workspace.id, memberId);
      load();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Members</h1>
      <p className="mt-1 text-sm text-slate-500">
        {canManage
          ? "Invite teammates and manage roles."
          : "Only owners and admins can manage members."}
      </p>

      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {canManage && (
        <form
          onSubmit={handleInvite}
          className="mt-6 flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4"
        >
          <div className="min-w-[200px] flex-1">
            <label className="block text-xs font-medium text-slate-700" htmlFor="invite-email">
              Email
            </label>
            <input
              id="invite-email"
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              placeholder="teammate@company.com"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700" htmlFor="invite-role">
              Role
            </label>
            <select
              id="invite-role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as WorkspaceRole)}
              className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {ASSIGNABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={isInviting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {isInviting ? "Inviting..." : "Invite"}
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Email</th>
                <th className="px-4 py-2">Role</th>
                {canManage && <th className="px-4 py-2">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {members.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-2 font-medium text-slate-900">{m.name}</td>
                  <td className="px-4 py-2 text-slate-600">{m.email}</td>
                  <td className="px-4 py-2">
                    {canManage ? (
                      <select
                        value={m.role}
                        onChange={(e) => handleRoleChange(m.id, e.target.value as WorkspaceRole)}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                      >
                        {ASSIGNABLE_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <RoleBadge role={m.role} />
                    )}
                  </td>
                  {canManage && (
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleRemove(m.id)}
                        className="text-xs font-medium text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {members.length === 0 && <p className="p-4 text-sm text-slate-500">No members yet.</p>}
        </div>
      )}
    </div>
  );
}
