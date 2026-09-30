# Multi-Agent System

The spec's 12 "agents" are implemented as **service-boundary functions**,
not as separate LLM-driven processes — each one is deterministic,
rule-based Python that runs synchronously inside the precheck pipeline.
This is intentional: an agent that can be fully explained by reading a
function is easier to audit and trust than one whose behavior depends on
a model call, and the spec requires deterministic, non-destructive,
auditable behavior throughout.

| Spec agent | Code |
|---|---|
| 1. Document Intake Agent | `backend/app/routers/documents.py::upload_document` |
| 2. Document Quality Agent | `backend/app/services/defect_engine.py::generate_defects_from_document_quality` |
| 3. Requirement Agent | `backend/app/services/requirement_engine.py` |
| 4. Checklist Agent | `backend/app/services/checklist_engine.py` |
| 5. Attachment Reference Agent | `backend/app/services/attachment_engine.py` |
| 6. Metadata Agent | `backend/app/services/metadata_engine.py` |
| 7. Duplicate Agent | `backend/app/services/duplicate_engine.py` |
| 8. Defect Detection Agent | `backend/app/services/defect_engine.py` |
| 9. Objection Agent | `generate_defects_from_objections` + `routers/defects.py` |
| 10. Correction Agent | `routers/defects.py` correction endpoints (see docs/correction-workflow.md) |
| 11. Verification Agent | `backend/app/services/verification_engine.py::verify_defect` — re-runs the concrete check that produced the defect; never auto-resolves on a mere file change (see docs/defect-engine.md) |
| 12. Audit Agent | `backend/app/core/audit.py` |

Each function attributes its findings via `Defect.detected_by` (e.g.
`"ChecklistAgent"`, `"AttachmentReferenceAgent"`, `"MetadataAgent"`,
`"DuplicateAgent"`, `"DocumentQualityAgent"`, `"AuditAgent"`,
`"ObjectionAgent"`), so the origin of any finding is traceable in the API
response without needing to read the source.

## LLMProvider abstraction

`backend/app/services/llm_provider.py` implements the `LLMProvider`
interface with `MockProvider` / `OpenAIProvider` / `AnthropicProvider` /
`GroqProvider`. **No detection logic anywhere in this codebase depends on
an LLM call** — every engine above is rule-based and works identically
with or without any provider configured, which is what makes DEMO mode and
the entire test suite work with zero API keys (`MockProvider` performs no
network access). `OpenAIProvider`/`AnthropicProvider`/`GroqProvider` fall
back to `MockProvider` automatically if no API key is configured or if the
underlying API call fails for any reason — a missing key or a network
error never crashes a request. The provider is used only for one
supplementary, clearly-labeled thing: drafting non-binding correction
wording a human can edit. It is never consulted to decide whether a
requirement is met, a defect is real, or a case is compliant — see the
module's own docstring for the exact boundary, and
`tests/test_llm_provider.py::test_mock_provider_never_claims_resolution`
for the test enforcing it.

## Agents produce proposals, not actions

No function listed above calls any code that submits a filing, contacts an
external registry, or writes a `CONFIRMED`/`RESOLVED` status onto a
defect. The only code path that can do that is the human-approval gate in
`backend/app/routers/review.py`.
