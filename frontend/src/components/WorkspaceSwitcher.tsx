import type { Workspace } from "../api/types";

const CREATE_NEW_VALUE = "__create_new__";

interface WorkspaceSwitcherProps {
  workspaces: Workspace[];
  currentWorkspaceId: string;
  onSelect: (id: string) => void;
  onCreateNew: () => void;
}

export default function WorkspaceSwitcher({
  workspaces,
  currentWorkspaceId,
  onSelect,
  onCreateNew,
}: WorkspaceSwitcherProps) {
  return (
    <div>
      <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
        Workspace
      </label>
      <select
        value={currentWorkspaceId}
        onChange={(e) => {
          if (e.target.value === CREATE_NEW_VALUE) {
            onCreateNew();
          } else {
            onSelect(e.target.value);
          }
        }}
        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900"
      >
        {workspaces.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
        <option value={CREATE_NEW_VALUE}>+ Create new workspace...</option>
      </select>
    </div>
  );
}
