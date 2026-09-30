import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import { Loading, ErrorBox, SectionTitle } from "../components/Primitives";

export default function CasesPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: cases, isLoading, isError } = useQuery({ queryKey: ["cases"], queryFn: CasesAPI.list });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ case_reference: "", title: "", person_full_name: "", jurisdiction_note: "" });

  const createMutation = useMutation({
    mutationFn: CasesAPI.create,
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["cases"] });
      navigate(`/cases/${created.id}`);
    },
  });

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-display">Undertrial Liberty Sentinel</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)] mt-1">
            Never let a critical liberty-related event disappear inside a fragmented case record.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/settings" className="rounded-md px-4 py-2 text-sm font-medium border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-raised)]">
            Settings
          </Link>
          <button
            className="rounded-md px-4 py-2 text-sm font-medium bg-[color:var(--color-accent)] text-black hover:opacity-90"
            onClick={() => setShowForm((s) => !s)}
          >
            + New Case
          </button>
        </div>
      </div>

      {showForm && (
        <form
          className="card p-5 my-5 grid grid-cols-2 gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate(form);
          }}
        >
          <input required placeholder="Case reference (e.g. CR-2026-0142)" className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
            value={form.case_reference} onChange={(e) => setForm({ ...form, case_reference: e.target.value })} />
          <input required placeholder="Case title" className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
            value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input required placeholder="Person full name" className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
            value={form.person_full_name} onChange={(e) => setForm({ ...form, person_full_name: e.target.value })} />
          <input placeholder="Jurisdiction note (optional, descriptive only)" className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
            value={form.jurisdiction_note} onChange={(e) => setForm({ ...form, jurisdiction_note: e.target.value })} />
          <div className="col-span-2 flex justify-end gap-2">
            <button type="submit" className="rounded-md px-4 py-2 text-sm bg-[color:var(--color-accent)] text-black">
              Create Case
            </button>
          </div>
          {createMutation.isError && <div className="col-span-2"><ErrorBox message="Failed to create case. Check that the backend is running." /></div>}
        </form>
      )}

      <SectionTitle subtitle="Select a case to open its Command Center.">Cases</SectionTitle>

      {isLoading && <Loading />}
      {isError && <ErrorBox message="Could not load cases from the backend API." />}

      <div className="grid gap-3">
        {cases?.map((c) => (
          <button
            key={c.id}
            onClick={() => navigate(`/cases/${c.id}`)}
            className="card p-4 text-left hover:border-[color:var(--color-accent)] transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{c.title}</div>
                <div className="text-xs text-[color:var(--color-text-secondary)] mt-1">{c.case_reference}</div>
              </div>
              <div className="flex items-center gap-2">
                {c.is_demo && <span className="badge">DEMONSTRATION DATA</span>}
                <span className="badge">{c.status}</span>
              </div>
            </div>
          </button>
        ))}
        {cases?.length === 0 && <div className="text-sm text-[color:var(--color-text-muted)]">No cases yet. Create one, or run the demo seeder for offline demonstration data.</div>}
      </div>
    </div>
  );
}
