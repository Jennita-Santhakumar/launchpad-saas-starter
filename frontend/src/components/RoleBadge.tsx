import type { WorkspaceRole } from "../api/types";

const ROLE_STYLES: Record<WorkspaceRole, string> = {
  owner: "bg-purple-100 text-purple-800",
  admin: "bg-blue-100 text-blue-800",
  member: "bg-slate-100 text-slate-700",
};

export default function RoleBadge({ role }: { role: WorkspaceRole }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${ROLE_STYLES[role]}`}>
      {role}
    </span>
  );
}
