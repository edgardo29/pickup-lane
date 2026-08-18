# Production-Readiness Pass Plan: WS03-04A - Authorization Matrix Foundation And Route Drift Guard

## At A Glance

| Field | Value |
|---|---|
| Gate | `A - Executable-pass design` |
| Gate A date | `2026-08-18` |
| Branch | `pr/WS03-04` |
| Accepted baseline | `22855d0d0b8e67be733de1fea6e3771f0587cfa9` |
| Parent pass | `WS03-04 - Complete authorization matrix and negative proof` |
| Executable pass | `WS03-04A - Authorization matrix foundation and route drift guard` |
| Frozen Stage 0 intake | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Frozen intake SHA-256 | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` |
| Approved dependency graph | `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D` |
| Primary controls | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017` |
| Supporting authority | `IDB-01`, `IDB-02`, `IDB-03`, `IDB-04`; accepted `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B`; EN-01 trusted-test conventions |
| Canonical plan path | `docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md` |
| Planned requirement declaration | `backend/tests/support/requirements/ws03_04a.json` |
| Planned trusted evidence scope | `backend/tests/workflows/authorization_matrix_foundation` |
| Gate A outcome | `READY FOR GATE B AFTER HUMAN APPROVAL` |

## 1. Purpose

`WS03-04A` creates the source-derived authorization matrix foundation for the `WS03-04` parent. It inventories the current FastAPI route/action surface, assigns each route/action to the approved behavioral child owner or an explicit non-WS03-04 disposition, records the authorization dimensions each later child must prove, and adds a route drift guard so new or changed routes cannot bypass the matrix unnoticed.

This pass intentionally does not prove final route behavior for the user, relationship, admin, provider, runtime, export, unmask, or audit surfaces. Those closures remain owned by `WS03-04B`, `WS03-04C`, `WS03-04D`, or later named owners as recorded in the approved intake.

## 2. Authority Read

| Source | Gate A meaning |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Durable repository documents and approved frozen artifacts are authority. Gate A may create only the canonical plan and must stop before implementation. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Current accepted `develop`, accepted pass records, non-legacy trusted tests, and frozen SHA approvals define repository truth. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | Gate A must verify the frozen intake SHA, create the canonical plan, identify exact Gate B editable files and expected final files, then stop for human approval. |
| `docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md` | This plan must freeze requirements, scope, implementation files, evidence, validation, risks, non-goals, and stop conditions. |
| `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` | Gate B testing evidence must include a human risk and adequacy record separate from machine requirement traceability. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | `WS03-01`, `WS03-02`, `WS03-03A`, and `WS03-03B` are accepted. `WS03-04` is not yet recorded as started, so the first substantive child pass must update the register. |
| Frozen `WS03-04` intake | The approved child graph and parent obligation allocation are frozen for this Gate A run. `WS03-04A` runs first and is the only child authorized for Gate A here. |
| Master blueprint | `WS03-04` must inventory every protected route/action and enforce object, relationship, workflow-state, list/query, field, function, role, and concealment boundaries. |
| Final remediation plan | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, and `IAM-017` remain partial; complete negative authorization proof needs route, object, nested resource, relationship, state, list/search, field, function, admin action, stale-role, mass-assignment, and 401/403/404 substitution coverage. |
| Decision Packet 2 | `IDB-01` through `IDB-04` fix replay, identity authority, verified-email, and App Check boundaries. App Check does not replace backend authorization. |
| Accepted predecessor plans and evidence | `WS03-01` and `WS03-02` are prerequisite repository source/test truth for identity and account state. `WS03-03A/B` are supporting repository source/test truth for recent-auth and App Check boundaries. These are not external evidence. |
| Repository standards | Backend routes own HTTP dependencies, services own authorization by target record/state, frontend guards are not backend authorization, `backend/tests/legacy/` is excluded, and tests must use the lowest reliable trusted layer. |
| Current source | Current `backend/main.py` registers 289 `APIRoute` entries and 289 flattened route keys excluding `HEAD`/`OPTIONS`. FastAPI route dependencies are deterministically representable through recursive `APIRoute.dependant.dependencies` traversal; backend authorization dependencies are centralized through `backend/services/auth_service.py`; route modules, schemas, and models expose the current resource and state model needed for matrix classification. |

## 3. Frozen Inputs And Prerequisite Verdict

| Check | Result |
|---|---|
| Branch | `pr/WS03-04` verified. |
| Accepted baseline | `HEAD` and merge-base with `develop` verified as `22855d0d0b8e67be733de1fea6e3771f0587cfa9`. |
| Intake SHA | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` verified as `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`. |
| Approved child graph | Preserved exactly as `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D`. |
| `WS03-01` prerequisite | Accepted in the execution register and available as repository source/test evidence. |
| `WS03-02` prerequisite | Accepted in the execution register and available as repository source/test evidence. |
| Stable resource/state models | Satisfied for `WS03-04A` design: current route modules, schemas, and models expose concrete user, game, booking, participant, waitlist, chat, Need-a-Sub, payment, refund, credit, notice, support, and admin states. |
| Supporting `WS03-03A/B` state | Accepted and relevant as compatibility boundaries, not as substitutes for authorization. |
| Current route inventoryability | Ready: route table generation succeeds from current `backend.main.app`. |

Prerequisite verdict: `READY FOR GATE B AFTER HUMAN APPROVAL`.

No prerequisite blocks `WS03-04A`. The intake remains frozen and is not Gate B-editable.

## 4. Gate A Outcome

Gate A outcome: `READY FOR GATE B AFTER HUMAN APPROVAL`.

`WS03-04A` is designed as a repository-truth matrix and guard pass. Gate B will create a canonical structured authorization matrix, a trusted pytest guard for current route drift and matrix completeness, a requirement declaration, a human testing record, and the first-child execution-register update.

This plan does not authorize application source changes. If Gate B discovers that a production-source correction is required to create or validate the matrix, Gate B must stop and request a Gate A correction or a new owner decision instead of modifying source under this pass.

### Executable-Child Cohesion And Safe State

| Gate A question | Verdict |
|---|---|
| One primary outcome | Yes. `WS03-04A` produces the canonical authorization matrix foundation and route/dependency drift guard that later WS03-04 children consume. |
| Coherent requirement/invariant family | Yes. All requirements protect the same foundation invariants: complete source-derived route inventory, traceable authorization classification, child/disposition ownership, gap registration, and fail-closed drift detection. |
| One safe merge/rollback or forward-fix unit | Yes. The pass is artifact/test/register focused and does not alter application behavior. Rollback removes the foundation artifacts and proposed register state; forward fixes update the matrix/guard when route authority changes. |
| Independently safe and useful merged state | Yes. After merge, product behavior is unchanged, parent `WS03-04` remains incomplete, and future unclassified route or authorization-dependency drift is visible before B/C/D behavioral closure work proceeds. |
| Behavioral-closure boundary | Preserved. A establishes the matrix/drift foundation without claiming B/C/D authorization behavior, provider/runtime evidence, export/unmask policy, or final parent closure. |
| Stage 0 boundary | Preserved. The approved Stage 0 child boundary still fits and does not require another split, combination, owner decision, or Stage 0 revision. File count, route count, test count, and pass size do not drive this boundary. |

## 5. Requirements

| Requirement ID | State | Scope | Source controls | Requirement |
|---|---|---|---|---|
| `WS03-04A-R1` | `required` | `workflows/authorization_matrix_foundation` | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `WS03-04` | The authorization matrix must enumerate every current registered FastAPI `APIRoute` method/path pair except implicit `HEAD` and `OPTIONS`, including public, health, provider-callback, retired/tombstone, authenticated, self-owned, relationship, and admin routes. |
| `WS03-04A-R2` | `required` | `workflows/authorization_matrix_foundation` | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `GOV-006`, `WS03-04` | The matrix artifact must use a structured schema that records route identity, source metadata, deterministically serialized authorization dependencies, route disposition and disposition reason, behavioral owner and owner reason, negative-proof owner/detail/reason, actor, resource, relationship, workflow-state, list/query, field, function, role, concealment, and canonical gap-reference fields. Detailed risk and adequacy analysis belongs in `TESTING_RECORD.md`, not in a matrix risk taxonomy. |
| `WS03-04A-R3` | `required` | `workflows/authorization_matrix_foundation` | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `WS03-04B`, `WS03-04C`, `WS03-04D` | Every route/action must have exactly one behavioral child owner of `WS03-04B`, `WS03-04C`, or `WS03-04D`, or an explicit non-WS03-04 disposition, every family must be homogeneous for behavioral ownership, and mixed high-level prefixes must be split into explicit matrix families. There must be no `WS03-04A` behavioral ownership, missing owner, unsupported overlap, broad prefix-only allocation, or stale route entry. |
| `WS03-04A-R4` | `required` | `workflows/authorization_matrix_foundation` | `IAM-012`, `IAM-016`, `IDB-01`, `IDB-02`, `IDB-03`, `IDB-04`, `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B` | Protected routes must be classified from backend dependencies and source policy, not frontend route guards. Every route must carry a non-empty `disposition_reason`; public, optional-auth, provider-callback, health/root, retired/tombstone, and excluded routes must explain why they are outside ordinary protected-route authorization. |
| `WS03-04A-R5` | `required` | `workflows/authorization_matrix_foundation` | `IAM-013`, `IAM-015`, `IAM-017`, `ADM-007`, `ADM-013`, `ADM-015`, `WS03-04` | The matrix must identify the required authorization dimensions and expected negative-proof owner/detail/reason for object IDs, nested resources, relationships, workflow states, list/search/aggregate/export-like surfaces, writable fields, function/action gates, role/current-account checks, and 401/403/404/410 concealment semantics. |
| `WS03-04A-R6` | `required` | `workflows/authorization_matrix_foundation` | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `TST-005`, `WS03-04` | A route and authorization-dependency drift guard must fail closed when current registered routes are missing from the matrix, stale matrix entries are no longer registered, deterministically serialized backend authorization dependencies differ from the current nested FastAPI dependency tree, a protected route lacks a backend auth classification, or a route/action contains undefined authorization policy without an explicit owner/blocker disposition. |
| `WS03-04A-R7` | `required` | `workflows/authorization_matrix_foundation` | `EN-01`, `GOV-006`, `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B`, `WS03-04` | Requirement declaration, pytest markers, testing record, and matrix metadata must be traceable to accepted repository source/test truth, accurately classify accepted predecessor evidence, and avoid `backend/tests/legacy/`. |
| `WS03-04A-R8` | `required` | `workflows/authorization_matrix_foundation` | `IAM-010`, `IAM-011`, `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `WS03-04` | Negative-space evidence must prevent false closure from frontend-only guards, App Check, recent-auth, broad active-admin checks, provider/runtime observations, generated OpenAPI alone, or local pytest mappings to external/provider/governance facts. |
| `WS03-04A-R9` | `deferred` | `governance` | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `WS03-04B`, `WS03-04C`, `WS03-04D`, `WS04`, `WS08`, `WS09`, `WS10` | Final behavioral authorization closure for self-owned surfaces, game/community/Need-a-Sub relationship surfaces, admin/high-risk surfaces, provider/runtime substitution proof, database concurrency proof, export/unmask/read-audit policy, and final parent gap disposition remains outside `WS03-04A` and must have zero pytest mappings in this pass. |

The planned requirement declaration is `backend/tests/support/requirements/ws03_04a.json`. It must declare `R1` through `R8` as `required` with scope `workflows/authorization_matrix_foundation`, and `R9` as `deferred` with scope `governance`.

## 6. Technical Design

### Canonical Matrix Artifact

Gate B must create `backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json` as the single structured source for the `WS03-04A` matrix foundation.

The artifact must use JSON so tests can parse it without ad hoc Markdown parsing. It must include these top-level fields:

```json
{
  "schema_version": 1,
  "pass_id": "WS03-04A",
  "parent_pass": "WS03-04",
  "accepted_baseline_sha": "22855d0d0b8e67be733de1fea6e3771f0587cfa9",
  "frozen_intake": {
    "path": "docs/production-readiness/planning/passes/ws03/ws03-04-intake.md",
    "sha256": "e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4"
  },
  "child_dependency_graph": "WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D",
  "route_key_format": "METHOD path_format",
  "excluded_methods": ["HEAD", "OPTIONS"],
  "baseline_apiroute_count": 289,
  "baseline_flattened_route_key_count": 289,
  "auth_dependency_serialization": {
    "version": 1,
    "route_tree": "APIRoute.dependant.dependencies recursive traversal",
    "identity_format": "module:qualname",
    "recorded_value": "sorted unique backend.services.auth_service dependency identities"
  },
  "sources": [],
  "route_families": [],
  "uncovered_gaps": []
}
```

`baseline_apiroute_count` means the number of current registered `APIRoute` objects in `backend.main.app`. `baseline_flattened_route_key_count` means the number of unique `(method, path_format)` pairs after excluding `HEAD` and `OPTIONS`. Current source produces `289` for both counts. Tests must compare each field to the matching source-derived count and must not use one ambiguous route-count value for both concepts.

### Source Traceability Contract

Top-level `sources[]` is the only source-traceability registry for the matrix artifact. Every `source_id` referenced by a family, route, or uncovered gap must exist in `sources[]`.

Each `sources[]` entry must include:

| Field | Required meaning |
|---|---|
| `source_id` | Unique stable identifier such as `SRC-001`. |
| `source_type` | One of `durable_doc`, `workflow`, `template`, `execution_register`, `frozen_intake`, `blueprint`, `remediation_plan`, `decision_record`, `accepted_predecessor_plan`, `repository_source`, `repository_test_standard`, or `current_route_table`. |
| `path` | Repository-relative path for repository sources. For generated current route-table evidence, use `backend.main.app` and explain generation in `description`. |
| `title` | Human-readable source title. |
| `authority_role` | One of `authority`, `frozen_boundary`, `accepted_repository_evidence`, `repository_truth`, `standard`, or `derived_current_truth`. |
| `evidence_classification` | One of `durable_authority`, `repository_truth`, `accepted_repository_source_test_evidence`, `governance_boundary`, or `derived_inventory`. Accepted WS03 predecessor source/test evidence must use `accepted_repository_source_test_evidence`, not external evidence. |
| `description` | Concise reason this source is relevant to matrix classification, gap disposition, or validation. |

Source invariants:

- `source_id` values are unique.
- all `source_ids` referenced by route families, route entries, or `uncovered_gaps` resolve to a top-level source;
- repository paths exist at Gate B unless the source is the generated `current_route_table` entry;
- no source path may reference `backend/tests/legacy/`;
- route/family/gap claims about accepted predecessor evidence must classify it as repository source/test evidence;
- derived source entries must identify the repository mechanism that derives them, for example `backend.main.app` route enumeration.

### Uncovered-Gap Register Contract

Top-level `uncovered_gaps[]` is the canonical uncovered-gap register for `WS03-04A`. Route and family entries must not carry independent `gap_state` or `gap_reason` fields. They may only reference top-level gaps through `gap_refs`.

Ordinary B/C/D behavioral child ownership is recorded directly on route/family entries and is not, by itself, an uncovered gap. Every unresolved blocker must be represented in top-level `uncovered_gaps[]`; no blocker or unresolved gap may live only in `owner_reason`, `disposition_reason`, owner-detail fields, the testing record, or prose. If `WS03-04A` records a later-child handoff as an unresolved gap because proof is deferred, the gap must use `owned_by_later_child` with a named owner and concrete reason. Unresolved `owned_by_later_child` and `deferred_external` facts exist only in the canonical top-level register.

An already-established `covered_elsewhere` disposition may remain a direct route/family ownership disposition when there is no unresolved gap, but it must still name the actual downstream owner in the owner-detail fields. Any remaining proof gap for a `covered_elsewhere` route/family must use `uncovered_gaps[]` with reciprocal `gap_refs`.

Each `uncovered_gaps[]` entry must include:

| Field | Required meaning |
|---|---|
| `gap_id` | Unique stable identifier such as `WS03-04A-G001`. |
| `state` | One of `owned_by_later_child`, `covered_elsewhere`, `deferred_external`, or `blocked_owner_decision`. |
| `title` | Short human-readable gap title. |
| `reason` | Concrete reason the gap is not closed by `WS03-04A`. |
| `owner` | Named downstream child, later pass, evidence owner, or governance owner. Use `WS03-04B`, `WS03-04C`, `WS03-04D`, `WS04`, `WS08`, `WS09`, `WS10`, a specific covered-elsewhere pass/control owner, or `owner_decision_required` as applicable. |
| `owner_type` | One of `child_pass`, `later_pass`, `external_evidence`, `governance_owner`, or `covered_elsewhere`. |
| `source_ids` | Non-empty list of source IDs supporting the gap/disposition. |
| `requirement_ids` | Non-empty list of related `WS03-04A` requirement IDs. |
| `affected_families` | List of affected matrix `family_id` values. Family-level gaps must list every affected family and each affected family must reference the gap through `gap_refs`. |
| `affected_routes` | Exact route keys as objects with `method` and `path` when the gap is route-specific. Family-level gaps may use an empty list only if `affected_families` is non-empty. |
| `resolution_condition` | What must happen for the gap to be closed, deferred to an accepted later owner, or removed. |
| `blocks_ws03_04a_acceptance` | Boolean. Must be `true` for `blocked_owner_decision`; must be `false` for ordinary B/C/D ownership handoffs and valid covered-elsewhere/deferred-external records. |

Gap invariants:

- `gap_id` values are unique.
- every route and family `gap_refs[]` value resolves to exactly one top-level gap;
- every gap `source_ids[]` value resolves to `sources[]`, every `requirement_ids[]` value is a valid `WS03-04A-R1` through `WS03-04A-R9` requirement, every affected route exists in the matrix, and every affected family exists in the matrix;
- every top-level route-specific gap has reciprocal route `gap_refs` on each affected route, and every family-level gap has reciprocal family `gap_refs` on each affected family;
- no top-level gap may be orphaned: it must name affected routes, affected families, or requirement IDs with a concrete reason;
- every route or family whose owner/disposition is `blocked` must reference a `blocked_owner_decision` gap;
- unresolved `owned_by_later_child` and `deferred_external` records may appear only in `uncovered_gaps[]`, never as free-text-only route/family annotations;
- any `covered_elsewhere`, `deferred_external`, or `blocked` route/family disposition must have a concrete reason and a named downstream/evidence/governance owner either directly on the route/family for already-established covered-elsewhere facts or through a referenced top-level gap for unresolved gaps;
- `blocked_owner_decision` gaps must set `blocks_ws03_04a_acceptance` to `true` and prevent a ready-for-acceptance Gate B result until resolved;
- gap records must not contradict route/family ownership, for example a route cannot be assigned to `WS03-04B` for behavioral proof while its only gap says the whole route is `not_applicable`;
- removing a route or family gap requires removing all reciprocal `gap_refs`, or the contract must fail;
- stale, orphaned, contradictory, one-sided, or prose-only gap references fail validation.

Each `route_families[]` entry must include:

| Field | Required meaning |
|---|---|
| `family_id` | Stable lowercase identifier, for example `games`, `admin_money`, or `need_a_sub_posts`. |
| `summary` | Short human-readable family description. |
| `primary_child_owner` | One of `WS03-04B`, `WS03-04C`, `WS03-04D`, `covered_elsewhere`, `not_applicable`, or `blocked`. `WS03-04A` is not a valid behavioral owner because A owns the matrix foundation and drift guard, not route/family closure. |
| `owner_reason` | Why this owner/disposition is correct under the approved intake. |
| `behavior_owner_detail` | Actual named downstream behavioral owner. For `WS03-04B`, `WS03-04C`, or `WS03-04D`, this must equal `primary_child_owner`. For `covered_elsewhere`, name the later pass/control owner such as `WS05`. For `blocked`, use `owner_decision_required` or a named governance owner and reference a `blocked_owner_decision` gap. |
| `source_ids` | Non-empty list of source IDs supporting the family allocation. |
| `gap_refs` | List of top-level `gap_id` values affecting the family. Empty means the family has no family-level uncovered gap in the A foundation. |
| `routes` | Explicit list of method/path entries. No wildcard-only family ownership. Every route in the family must use the same behavioral owner/disposition as `primary_child_owner`; mixed high-level prefixes must be split into separate matrix families inside this artifact, not new executable passes. |

Each `routes[]` entry must include:

| Field | Required meaning |
|---|---|
| `method` | Registered HTTP method other than implicit `HEAD` or `OPTIONS`. |
| `path` | FastAPI `path_format`, not a concrete sample URL. |
| `name` | Registered route name. |
| `tags` | Registered FastAPI tags. |
| `source_module` | Module owning the route endpoint when available. |
| `auth_dependencies` | Deterministically serialized backend authorization dependency identities discovered from the route dependency tree, including nested auth helpers, using the authorization-dependency serialization contract below. |
| `route_disposition` | One of `protected`, `public`, `optional_auth`, `provider_callback`, `health_or_root`, `retired_or_tombstone`, or `excluded_non_api`. |
| `disposition_reason` | Non-empty reason for the route disposition. For public, optional-auth, provider-callback, health/root, retired/tombstone, and excluded routes, it must explain why the route is outside ordinary protected-route authorization. For protected routes, it must identify the backend auth classification basis. |
| `child_owner` | One of `WS03-04B`, `WS03-04C`, `WS03-04D`, `covered_elsewhere`, `not_applicable`, or `blocked`, but specific to the route/action. `WS03-04A` is not allowed here. |
| `owner_reason` | Non-empty reason why the behavioral owner/disposition is correct under the approved intake and current route family allocation. This is separate from `disposition_reason`, which explains HTTP/auth disposition. |
| `behavior_owner_detail` | Actual named downstream behavioral owner. For B/C/D-owned routes, this must equal `child_owner`. For `covered_elsewhere`, name the later pass/control owner. For `blocked`, use `owner_decision_required` or a named governance owner and reference a `blocked_owner_decision` gap. |
| `actor_classes` | Current actor categories, for example `anonymous`, `current_user`, `verified_user`, `active_user`, `host`, `participant`, `requester`, `target_user`, `admin`, `provider`. |
| `resource_family` | Primary resource family or `not_applicable`. |
| `resource_id_fields` | Path/body/query identifiers that require ownership, relationship, state, or admin proof. |
| `relationship_rules` | Relationship authorization dimensions such as owner, host, participant, buyer, request owner, message sender, chat member, target user, or admin reviewer. |
| `workflow_state_rules` | Status/state dimensions relevant to authorization, including user account status, game publish/status/visibility/join state, booking/payment/refund status, Need-a-Sub post/request status, notice state, support/review state, or `not_applicable`. |
| `list_query_rules` | List/search/aggregate/cursor/export-like scoping requirements or `not_applicable`. |
| `field_rules` | Writable/readable field boundary notes, mass-assignment relevance, response minimization relevance, or `not_applicable`. |
| `function_rules` | Action-specific permission/function gate notes, recent-auth preservation, idempotency/audit relevance, or `not_applicable`. |
| `role_rules` | Role/current-account requirements, including active-admin, verified-email, active-user, stale-role risk, or `not_applicable`. |
| `concealment_policy` | Expected denial/existence posture: `401`, `403`, `404`, `410`, `mixed`, `not_applicable`, or `blocked_owner_decision`. |
| `negative_proof_owner` | One of `WS03-04B`, `WS03-04C`, `WS03-04D`, `covered_elsewhere`, `not_applicable`, or `blocked`. |
| `negative_proof_owner_detail` | Actual named proof owner. For B/C/D-owned routes this must normally equal `child_owner` because the approved intake allocates implementation and negative proof by surface. For `covered_elsewhere` or `blocked`, it must identify the actual proof owner such as `WS05` or `owner_decision_required`; the generic enum value is not enough. |
| `negative_proof_reason` | Non-empty reason for the negative-proof owner. Required for every route; when it differs from `child_owner`, it must explain the exception and reference a canonical gap unless the route is already-established `covered_elsewhere` with no unresolved gap. |
| `source_ids` | Non-empty list of source IDs supporting route classification. |
| `gap_refs` | List of `gap_id` values in top-level `uncovered_gaps`. Empty means the route has no route-specific uncovered gap in the A foundation. |

The matrix may group routes into families for readability, but the tests must validate the flattened method/path set.

Ownership invariants:

- every route has exactly one `child_owner`;
- every family has exactly one `primary_child_owner`;
- every family is homogeneous for behavioral ownership: contained routes must use the same behavioral owner/disposition as the family;
- if a high-level prefix contains routes belonging to different behavioral owners, Gate B must split it into separate matrix families inside `authorization_matrix.json` rather than creating new executable passes or mixing owners in one family;
- `WS03-04A` is never a valid behavioral owner;
- B/C/D route ownership must stay within the approved intake allocation and must not introduce a B/C dependency;
- `covered_elsewhere` and `blocked` values must identify an actual owner through `behavior_owner_detail`, `negative_proof_owner_detail`, or a canonical gap as applicable.

Negative-proof invariants:

- for B/C/D-owned routes, `negative_proof_owner` must normally equal `child_owner`;
- a legitimate difference between behavioral owner and negative-proof owner must name the actual proof owner, include `negative_proof_reason`, and reference a canonical gap unless the route is an already-established `covered_elsewhere` disposition with no unresolved proof gap;
- `negative_proof_owner` values of `covered_elsewhere` or `blocked` must never stand alone; `negative_proof_owner_detail` must name the actual proof owner or `owner_decision_required`;
- blocked negative-proof ownership must reference a `blocked_owner_decision` gap and cannot produce a ready-for-acceptance Gate B result until resolved.

### Current Route-Family Allocation

Gate B must classify the current route table using this allocation:

| Route family / prefix or tag | Matrix disposition | Behavioral owner |
|---|---|---|
| `/`, `/live`, `/ready`, `/db-health` | Non-protected system/health/root routes with explicit reason | `not_applicable` unless a later platform pass changes health policy |
| `/stripe/webhook` | Provider callback outside user authorization; classify and hand off PAY-005/PAY-006 payment/webhook lifecycle proof without claiming it complete | `covered_elsewhere` / `WS05` |
| `/auth/*` | Identity/account lifecycle routes; classify predecessor-owned identity and B-owned self-account risks | `WS03-04B` where WS03-04 authorization remains |
| `/users/me`, `/user-settings/me`, `/user-stats/me` | Self-owned profile/settings/stats authorization | `WS03-04B` |
| `/users`, `/users/{user_id}`, `/user-settings/{user_id}`, `/user-stats/{user_id}` | Generic/admin user routes or disabled/tombstone routes | `WS03-04D` or `covered_elsewhere` for retired routes |
| `/user-payment-methods/*`, `/game-credits/*`, non-admin `/payments/*`, non-admin `/refunds/*`, `/host-publish-fees/*` | Self-owned financial/payment-method/credit/fee records | `WS03-04B` |
| `/notifications/*`, `/inbox/*` | Self-owned notification and inbox records, with platform notice read-state distinctions | `WS03-04B` |
| `/games/*`, `/community-games/*`, `/community-game-details/*`, `/checkout/*`, `/bookings/*`, `/game-participants/*`, `/waitlist-entries/*`, `/game-chats/*`, `/chat-messages/*`, `/my-games/*` | Game, community, roster, booking, checkout, waitlist, and chat relationship authorization | `WS03-04C` |
| `/need-a-sub/posts/*`, `/need-a-sub/requests/*`, Need-a-Sub status/history/position routes | Need-a-Sub owner/requester/chat/status relationship authorization | `WS03-04C` |
| `/venues/*`, `/venue-images/*`, `/venue-approval-requests/*`, `/game-images/*`, policy-document and policy-acceptance scaffold routes | Admin, public, retired, or later policy/data-owner authorization according to current dependency/status | `WS03-04B`, `WS03-04C`, `WS03-04D`, or `covered_elsewhere` per exact route |
| `/admin/*` | Admin route, list, read, mutation, high-risk function, stale-role, and active-admin authorization | `WS03-04D` |

These rows are current-route classification inputs, not permission to create mixed-owner matrix families. Any row whose current routes belong to multiple behavioral owners or dispositions must be split into separate homogeneous `route_families[]` entries in the matrix artifact.

The allocation must not impose a `WS03-04B -> WS03-04C` dependency. B and C may run independently after A. D remains after both B and C because it owns final admin/high-risk review and parent-gap disposition.

### Authorization-Dependency Serialization Contract

Gate B must use one deterministic normalization helper for both the recorded matrix value and the current FastAPI comparison.

Current source inspection shows every dependency callable reachable from `backend.main.app` has a module-qualified callable identity, no callable-object dependency identity is currently required, and no identity collision was found. The current app has repeated nested auth helpers on many routes, especially `get_verified_firebase_identity`, so duplicate occurrences are expected and must be normalized deterministically.

The normalization contract is:

1. For each `APIRoute`, start from `route.dependant.dependencies`. Exclude the root endpoint callable itself.
2. Traverse each `Dependant.dependencies` tree recursively in FastAPI's stored order so direct and nested dependencies are both considered.
3. A backend authorization dependency is any traversed dependency whose callable identity starts with `backend.services.auth_service:`. `backend.database:get_db`, request/body/query/header parameters, middleware such as App Check, and service calls made inside endpoint bodies are not recorded in `auth_dependencies`.
4. Serialize normal functions and bound or unbound methods as `<callable.__module__>:<callable.__qualname__>`. Bare `__name__` values are not sufficient.
5. If a callable has `__wrapped__`, serialize the stored FastAPI callable plus the wrapper chain as `<module>:<qualname>[wrapped=<module>:<qualname>]`, repeated from outermost to innermost. Wrapper cycles or missing module/qualname data fail validation.
6. `functools.partial`, callable objects, lambdas, nested local functions, dynamically generated functions without stable module/qualname, or two distinct callable objects producing the same identity are unrepresentable under this plan and must fail Gate B validation until a Gate A correction defines a stable representation.
7. Normalize each route's recorded value as a lexicographically sorted unique list of serialized backend authorization dependency identities. Duplicate occurrences of the same identity are collapsed after identity validation; distinct identities must never be collapsed to a bare name.

Current backend authorization dependency identities observed in the route tree are:

```text
backend.services.auth_service:get_current_app_user
backend.services.auth_service:get_optional_current_app_user
backend.services.auth_service:get_synced_current_app_user
backend.services.auth_service:get_verified_firebase_identity
backend.services.auth_service:require_active_admin
backend.services.auth_service:require_active_user
backend.services.auth_service:require_recent_active_admin
backend.services.auth_service:require_recent_active_user
backend.services.auth_service:require_recent_app_user
backend.services.auth_service:require_recent_authentication
backend.services.auth_service:require_verified_user
```

If an unchanged method/path has a different normalized authorization-dependency list from the recorded matrix, the contract fails closed until the matrix is deliberately reviewed and updated with source traceability.

### Route Drift Guard

Gate B must create `backend/tests/workflows/authorization_matrix_foundation/test_authorization_matrix_foundation_contract.py` with local helpers that:

1. Import `backend.main.app`.
2. Enumerate all `APIRoute` instances and flatten route keys as `(method, path_format)`, excluding `HEAD` and `OPTIONS`.
3. Load `authorization_matrix.json`.
4. Assert the matrix route-key set equals the current registered route-key set.
5. Assert stale matrix routes, duplicate routes, missing routes, and new unclassified routes fail with readable diagnostics.
6. Assert recorded `auth_dependencies` for every route match the current FastAPI dependency tree using the authorization-dependency serialization contract above, including nested auth helpers. A changed auth dependency on an unchanged method/path route must fail the contract until the matrix is deliberately reviewed and updated.
7. Assert `baseline_apiroute_count` equals the current `APIRoute` object count and `baseline_flattened_route_key_count` equals the current flattened route-key count, both currently `289`.
8. Assert each protected route has an authorization classification derived from backend route dependencies/source, and each public/optional/provider/health/retired route has an explicit non-empty `disposition_reason`.
9. Assert deferred/governance requirement `WS03-04A-R9` has zero pytest mappings.

### Matrix Validation Rules

The test file must validate:

- required top-level JSON fields and `schema_version == 1`;
- `pass_id`, parent pass, accepted baseline, frozen intake path, frozen intake SHA, and approved dependency graph;
- exact `baseline_apiroute_count` and `baseline_flattened_route_key_count` semantics and values;
- exact `auth_dependency_serialization` metadata and shared normalization helper semantics;
- exact `sources[]` schema, unique `source_id` values, valid source references from families/routes/gaps, existing repository paths, and no legacy-test references;
- exact `uncovered_gaps[]` schema, unique `gap_id` values, reciprocal route/family `gap_refs`, non-orphaned gap records, concrete reasons, valid source/route/family/requirement references, named owners, no one-sided references, and no contradictory gap/ownership pairings;
- required route-family and route-entry fields;
- exact child owner/disposition vocabulary with no `WS03-04A` route or family behavioral owner;
- every family has exactly one `primary_child_owner`, every route has exactly one `child_owner`, and every family is homogeneous for behavioral ownership;
- mixed high-level prefixes are split into separate explicit matrix families rather than carrying multiple owners inside one family;
- `covered_elsewhere` and `blocked` route/family ownership values identify actual owners through detail fields and canonical gaps where unresolved;
- non-empty `disposition_reason` on every route, with non-protected dispositions explaining why they are outside ordinary protected-route authorization;
- non-empty route `owner_reason`, `negative_proof_owner_detail`, and `negative_proof_reason` values, with B/C/D-owned routes normally keeping `negative_proof_owner == child_owner`;
- any exception where `negative_proof_owner` differs from `child_owner` names the actual proof owner, explains why, and references a canonical gap unless the route is an already-established `covered_elsewhere` disposition with no unresolved proof gap;
- recorded `auth_dependencies` exactly match the current nested FastAPI dependency tree for every route key under the frozen serialization algorithm, and ambiguous callable identity fails instead of reducing to a bare name;
- no broad prefix-only owner without explicit route entries;
- no route- or family-level `gap_state` or `gap_reason`; top-level `uncovered_gaps[]` is the one authoritative gap model and routes/families may only link to it through `gap_refs`;
- no `blocked` owner or `blocked_owner_decision` in a ready-for-acceptance Gate B result; blocked ownership requires an explicit blocked disposition and reason, and the Gate B result must remain blocked until resolved;
- no child-owner overlap for any method/path key;
- no route classified only by frontend route guards;
- no direct reference to `backend/tests/legacy/`;
- no local pytest mapping to external provider/runtime/governance closure.

### Testing Record

Gate B must create `backend/tests/workflows/authorization_matrix_foundation/TESTING_RECORD.md` using the testing-record template. It must state:

- trusted scope: `backend/tests/workflows/authorization_matrix_foundation`;
- requirement declaration: `backend/tests/support/requirements/ws03_04a.json`;
- canonical matrix artifact: `authorization_matrix.json`;
- authoritative sources read;
- risk model for skipped route, stale route, owner overlap, route/family ownership mismatch, unnamed covered-elsewhere or blocked owner, negative-proof owner drift, canonical gap/reference corruption, ambiguous authorization dependency identity, undefined policy, frontend-only guard, false provider/runtime closure, and sibling-child overclaim;
- route/action scenario discovery method;
- failure transformations and side effects;
- selected evidence and adequacy criteria;
- unresolved gaps, canonical gap-reference integrity, and downstream owners;
- explicit statement that `R9` is deferred/governance with zero pytest mappings.

## 7. Implementation Scope

Gate A editable scope is exactly this file:

```text
docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
```

Gate B editable file set is exactly:

```text
backend/tests/support/requirements/ws03_04a.json
backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json
backend/tests/workflows/authorization_matrix_foundation/test_authorization_matrix_foundation_contract.py
backend/tests/workflows/authorization_matrix_foundation/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

Gate B must not edit the frozen intake or this frozen plan. Gate B must not edit application source, frontend source, migrations, provider configuration, runtime configuration, or evidence outside the listed files.

Expected final changed-file set for the `WS03-04A` pass after Gate B is exactly:

```text
docs/production-readiness/planning/passes/ws03/ws03-04-intake.md
docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
backend/tests/support/requirements/ws03_04a.json
backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json
backend/tests/workflows/authorization_matrix_foundation/test_authorization_matrix_foundation_contract.py
backend/tests/workflows/authorization_matrix_foundation/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

The intake and plan are frozen artifacts carried by the first substantive child pass. They are not Gate B-editable.

## 8. Impact Scan

| Area | Gate B action |
|---|---|
| `backend/main.py` | Read/import current app route table only. No source edit. |
| `backend/routes/*.py` | Read route dependencies and registered paths through FastAPI metadata/source review. No source edit. |
| `backend/services/auth_service.py` | Use current module-qualified dependency identities as repository truth for identity/account/admin/recent-auth classification. No source edit. |
| `backend/models/*.py` and `backend/schemas/*.py` | Read current status, ownership, relationship, and field surfaces for matrix classification. No source edit. |
| `backend/tests/support/requirements/` | Add `ws03_04a.json`. |
| `backend/tests/workflows/authorization_matrix_foundation/` | Add trusted workflow scope, matrix artifact, test contract, and testing record. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Prepare the proposed first-child register state that becomes true only when the substantive PR merges into `develop`. |
| Frontend source | No Gate B edit. Frontend route guards/callers may be mentioned only as context, not as authorization proof. |
| Database/migrations | No Gate B edit or migration rehearsal expected. |
| Provider/runtime/staging | No Gate B proof or configuration. |
| `backend/tests/legacy/` | Excluded. Do not read, list, execute, cite, or map it. |

## 9. Testing And Evidence Plan

| Evidence artifact | Requirements | Expected proof |
|---|---|---|
| `backend/tests/support/requirements/ws03_04a.json` | `R1`-`R9` | Machine-readable declarations with `R1`-`R8` required and scoped to `workflows/authorization_matrix_foundation`; `R9` deferred/governance with zero pytest mappings. |
| `authorization_matrix.json` | `R1`-`R7` | Structured current-route matrix with baseline, intake SHA, child graph, source traceability registry, route families, route entries, policy dimensions, owner allocations, owner/disposition/negative-proof reasons, concealment posture, deterministic auth-dependency metadata, and canonical top-level uncovered-gap register. |
| `test_authorization_matrix_foundation_contract.py` | `R1`-`R8` | Pytest/static/dynamic checks for current route-key coverage, schema validity, child-owner partition, route/family homogeneity, negative-proof owner consistency, source/gap/route/family/requirement-reference integrity, dependency/disposition consistency, deterministic recorded-auth-dependency drift, undefined policy prevention, route drift failure, and false-closure prevention. |
| `TESTING_RECORD.md` | `R1`-`R9` | Human risk/evidence adequacy record, including canonical gap integrity, route/family ownership consistency, negative-proof ownership consistency, named covered-elsewhere/blocked owners, deterministic auth-dependency drift, reference integrity, unresolved gaps, and downstream owners. |
| `PASS-EXECUTION-REGISTER.md` | `R3`, `R7`, `R9` | Proposed first-child register state for `WS03-04A`, accepted intake reference, child graph, remaining children, and incomplete parent state that become true atomically on substantive PR merge. |

The test file should include at least these contract tests:

```text
test_authorization_matrix_includes_every_registered_route_key
test_authorization_matrix_schema_requires_authz_dimensions
test_authorization_matrix_source_and_gap_references_are_canonical
test_route_and_family_ownership_is_homogeneous_and_complete
test_negative_proof_owner_matches_behavioral_owner_or_records_exception
test_route_dispositions_match_backend_auth_dependencies
test_recorded_authorization_dependencies_match_current_fastapi_dependency_tree
test_child_owner_partition_has_no_gap_or_overlap
test_route_drift_validator_fails_for_missing_stale_or_duplicate_routes
test_negative_space_blocks_frontend_legacy_provider_and_deferred_false_closure
test_requirement_declaration_and_markers_match_ws03_04a_scope
```

Validation commands for Gate B:

```text
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04-intake.md
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
backend/.venv/bin/python -m py_compile backend/tests/workflows/authorization_matrix_foundation/test_authorization_matrix_foundation_contract.py
backend/.venv/bin/python -m pytest backend/tests/workflows/authorization_matrix_foundation
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/authorization_matrix_foundation
backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
git diff --check
git status --short --untracked-files=all
git diff --cached --name-only
```

Gate B must not run Playwright/e2e, provider, runtime/staging, migration, or broad backend API suites unless separately authorized.

## 10. Risk And Negative-Space Scenarios

| Scenario | Required Gate B response |
|---|---|
| A new route exists in FastAPI but not in the matrix | Test failure; route must be classified in the same authorized file set or the pass stops. |
| A stale matrix route is no longer registered | Test failure; remove or reclassify the stale route in the matrix under Gate B scope. |
| A route's method/path is unchanged but its backend authorization dependency changes | Test failure; recorded `auth_dependencies` must be reviewed and updated with source traceability. |
| A route is assigned to both B and C, or to a child and `covered_elsewhere` | Test failure; exactly one primary owner/disposition is required. |
| A family contains routes with different behavioral owners/dispositions | Test failure; split the high-level prefix into separate explicit matrix families inside `authorization_matrix.json`. |
| A B/C/D-owned route assigns negative proof to a different owner without a named proof owner, reason, and canonical gap/reference | Test failure; negative-proof ownership normally follows behavioral ownership, and exceptions must be explicit. |
| A `covered_elsewhere` route/family or proof owner uses only the generic enum and leaves the actual owner unnamed | Test failure; name the actual downstream owner, for example `WS05` for `/stripe/webhook` payment/webhook lifecycle proof. |
| A protected route has no backend auth dependency or public reason | Test failure; source change is not authorized in A, so Gate B must stop if classification reveals a real source defect. |
| A non-protected route lacks `disposition_reason` | Test failure; public/optional/provider/health/retired/excluded dispositions require an explicit reason. |
| A route- or family-level gap contradicts or bypasses the top-level gap register | Test failure; `uncovered_gaps[]` is authoritative and route/family `gap_refs` must be reciprocal and valid. |
| A blocked route/family or unresolved deferred gap exists only in prose fields | Test failure; unresolved blockers and deferred gaps must exist in canonical `uncovered_gaps[]`. |
| A gap references a missing route, family, requirement ID, or source ID | Test failure; source/gap/route/family/requirement reference integrity is mandatory. |
| An auth dependency callable cannot be serialized with the frozen deterministic identity rule | Blocking failure; Gate B must stop for Gate A correction rather than reducing it to a bare or ambiguous name. |
| A route depends only on frontend route guards for protection | Blocking failure; frontend guards are not backend authorization. |
| `unknown` or undefined policy appears without owner/blocker disposition | Test failure or blocked Gate B result, depending on whether a current owner decision can resolve it inside the exact file set. Blocked ownership requires an explicit blocked disposition and reason, and cannot produce a ready-for-acceptance Gate B result until resolved. |
| A deferred/provider/runtime/governance fact is mapped to local pytest | Test failure; deferred facts must stay unmapped. |
| `backend/tests/legacy/` appears in matrix, tests, or testing record | Test failure and scope correction required. |
| B/C/D behavioral authorization closure is claimed in A | Gate B report must correct the overclaim or stop for plan correction. |

## 11. Register Update Design

The first substantive `WS03-04A` Gate B change must prepare the proposed accepted-state update in `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`.

The register entries describe the state that becomes true atomically when the substantive PR merges into `develop`. Human Gate B or Gate C approval does not by itself make `WS03-04A` accepted.

The register update must:

- propose `WS03-04A` in accepted executable passes, with plan path `passes/ws03/ws03-04a-authorization-matrix-foundation.md`, requirement declaration `ws03_04a.json`, total requirements `9`, required `8`, blocked `0`, deferred `1`, and scope `workflows/authorization_matrix_foundation` plus governance;
- propose the frozen `WS03-04` intake record path and SHA in accepted Stage 0 intake records;
- propose a `WS03-04` parent decomposition section with approved children `WS03-04A`, `WS03-04B`, `WS03-04C`, and `WS03-04D`;
- propose the approved graph `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D`;
- propose parent `WS03-04` as incomplete after A, with B/C/D remaining;
- avoid claiming B, C, D, provider/runtime, named-permission, export/unmask, or read-audit closure.

## 12. Child Handoffs

| Child | Handoff from A |
|---|---|
| `WS03-04B` | Consume matrix entries for self-owned account, notification, inbox, saved-card, credit, payment, refund, and host-fee surfaces. Prove cross-user, list scope, state/account, field, recent-auth-preservation, and concealment behavior for those entries. |
| `WS03-04C` | Consume matrix entries for games, community games, checkout, bookings, participants, waitlists, chats/messages, My Games, and Need-a-Sub relationship surfaces. Prove host/participant/requester/message/resource/state/list/concealment behavior. |
| `WS03-04D` | Run after B and C. Consume matrix entries for admin routes, admin lists/searches, privileged functions, high-risk admin actions, and final uncovered-gap disposition. Decide whether parent closure is possible or blocked/deferred to named later owners. |

B and C have no hard dependency on each other after A. D follows both.

## 13. Non-Goals

- Do not begin Gate B without human approval of this plan and SHA.
- Do not edit the frozen Stage 0 intake.
- Do not edit application source, frontend source, migrations, provider configuration, runtime configuration, or unrelated docs under `WS03-04A`.
- Do not prove final user, game, Need-a-Sub, admin, provider, runtime, database-concurrency, export, unmask, read-audit, or production authorization behavior in A.
- Do not use frontend guards, App Check, recent-auth, broad active-admin checks, OpenAPI generation, or legacy tests as substitutes for backend authorization proof.
- Do not use `backend/tests/legacy/`.
- Do not stage, commit, push, or create/update a PR in Gate A or Gate B unless a later gate explicitly authorizes it.

## 14. Gate B Stop Conditions

Gate B must stop before acceptance if:

- the frozen intake SHA does not match `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`;
- this plan SHA does not match the human-approved Gate A SHA;
- any required file outside the exact Gate B editable file set must be modified;
- a current route family cannot be inventoried from FastAPI/source;
- any active route/action policy cannot be classified from current authority and source;
- any current FastAPI authorization dependency cannot be serialized deterministically under this plan;
- the approved child graph or B/C independence would need to change;
- frontend route guards are the only available authorization control for a backend operation;
- a deferred/provider/runtime/governance fact would need local pytest closure;
- the route drift guard cannot be made deterministic without source changes;
- `backend/tests/legacy/` would be needed for evidence.

## 15. Completion Criteria

`WS03-04A` Gate B is complete only when:

- the canonical matrix artifact covers every current registered route key and validates against this plan's schema;
- source traceability and uncovered-gap references are valid, reciprocal, non-orphaned, owner-named, and resolve every source, route, family, and requirement reference;
- every route/action has exactly one valid behavioral owner of `WS03-04B`, `WS03-04C`, or `WS03-04D`, or an explicit non-WS03-04 disposition, with a separate non-empty `owner_reason`;
- every family has exactly one `primary_child_owner`, contains only routes with the same behavioral owner/disposition, and splits mixed high-level prefixes into separate explicit families;
- B/C/D-owned routes keep `negative_proof_owner == child_owner` unless a named owner, reason, and canonical gap/reference justifies an exception;
- `covered_elsewhere` and `blocked` route/family/proof-owner values name the actual downstream owner, with `/stripe/webhook` payment/webhook lifecycle proof handed to `WS05` without claiming WS05 completion;
- no ready-for-acceptance result contains a `blocked` owner or `blocked_owner_decision`;
- every protected route has backend authorization classification and every public/optional/provider/health/retired route has an explicit reason;
- route and authorization-dependency drift tests fail closed for missing, stale, duplicate, unclassified, dependency-changed, and unrepresentable-dependency routes;
- requirement declarations and pytest markers pass domain and suite checker validation;
- `R9` remains deferred/governance with zero pytest mappings;
- `TESTING_RECORD.md` explains risk, scenario discovery, selected evidence, side effects, canonical gap integrity, route/family ownership consistency, negative-proof ownership consistency, named covered-elsewhere/blocked owners, deterministic auth-dependency drift, reference integrity, gaps, and adequacy;
- the execution register contains the proposed accepted intake, first-child, remaining-child graph, and incomplete-parent state that becomes true only on substantive PR merge, without overclaiming;
- the final changed files exactly match this plan's expected final changed-file set;
- `git diff --check` passes and nothing is staged.

## 16. Gate A Stop Boundary

Gate A stops after this canonical plan is created and its SHA-256 is reported for human approval. Gate A does not authorize Gate B, implementation, staging, committing, pushing, or PR work.
