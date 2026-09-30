import { useState } from "react";
import { getActingRole, setActingRole } from "../lib/api";

const ROLES = ["ANALYST", "REVIEWER", "ADMIN"];

export function RoleSwitcher() {
  const [role, setRole] = useState(getActingRole());
  return (
    <div className="text-xs">
      <label className="mb-1 block text-slate-500">Acting as (RBAC)</label>
      <select
        value={role}
        onChange={(e) => {
          setRole(e.target.value);
          setActingRole(e.target.value);
        }}
        className="w-full rounded-md border border-brand-border bg-brand-bg px-2 py-1 text-xs text-slate-200"
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </div>
  );
}
