import { useState } from "react";
import { Link } from "react-router-dom";
import { getDemoIdentity, setDemoIdentity, ROLES, api } from "../api/client";
import { SectionTitle } from "../components/Primitives";

const ROLE_DESCRIPTIONS: Record<string, string> = {
  CITIZEN: "Read-only. Cannot create cases, upload documents, resolve conflicts, or decide reviews.",
  LEGAL_AID: "Can create cases, upload documents, and add manual events. Cannot approve/reject reviews or resolve conflicts.",
  ADVOCATE: "Everything LEGAL_AID can do, plus resolving conflicts, recording verifications, and approving/rejecting review tasks.",
  ADMIN: "Full privilege, including any admin-only action reserved by the backend's role hierarchy.",
};

export default function SettingsTab() {
  const [identity, setIdentityState] = useState(getDemoIdentity());
  const [testResult, setTestResult] = useState<string | null>(null);

  const applyRole = (role: string) => {
    const next = { role, user: `frontend-demo-${role.toLowerCase()}` };
    setDemoIdentity(next);
    setIdentityState(next);
    setTestResult(null);
  };

  const testRbac = async () => {
    setTestResult("Testing…");
    try {
      await api.post("/api/cases", {
        case_reference: "RBAC-TEST", title: "RBAC test case", person_full_name: "Test Person",
      });
      setTestResult(`✓ Case creation ALLOWED for role ${identity.role}.`);
    } catch (e: any) {
      const detail = e?.response?.data?.error || e.message;
      setTestResult(`✗ Case creation BLOCKED for role ${identity.role}: ${detail}`);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <Link to="/" className="text-xs text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-accent)]">
        ← All cases
      </Link>
      <div className="card p-6 mt-4">
        <SectionTitle subtitle="This switches the DEMO identity sent as X-Demo-Role / X-Demo-User headers. Production deployments replace this with real JWT/session auth (see docs/security.md) -- this page exists to demonstrate the RBAC enforcement that already runs on every write endpoint.">
          Settings & Role-Based Access (Demo)
        </SectionTitle>

        <div className="space-y-3 mt-4">
          {ROLES.map((role) => (
            <button
              key={role}
              onClick={() => applyRole(role)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                identity.role === role
                  ? "border-[color:var(--color-accent)] bg-[color:var(--color-surface-raised)]"
                  : "border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-raised)]"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{role}</span>
                {identity.role === role && (
                  <span className="text-xs text-[color:var(--color-accent)]">Active</span>
                )}
              </div>
              <div className="text-xs text-[color:var(--color-text-secondary)] mt-1">
                {ROLE_DESCRIPTIONS[role]}
              </div>
            </button>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-[color:var(--color-border)]">
          <button
            onClick={testRbac}
            className="text-sm px-4 py-2 rounded-md bg-[color:var(--color-accent)] text-white hover:opacity-90"
          >
            Test: try creating a case as {identity.role}
          </button>
          {testResult && (
            <div className="mt-3 text-sm p-3 rounded-md bg-[color:var(--color-surface-raised)]">
              {testResult}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
