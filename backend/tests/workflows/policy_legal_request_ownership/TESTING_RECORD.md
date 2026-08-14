# WS02-04B2A2B3 Policy / Legal Request Ownership Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04B2A2B3` |
| Trusted test scope | `backend/tests/workflows/policy_legal_request_ownership` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04b2a2b3.json` |
| Authoritative sources | Canonical WS02-04B2A2B3 plan; applicable API/control requirements; EN-01 trusted evidence architecture |
| Evidence layers | pytest; FastAPI route-table proof; TestClient HTTP proof; PostgreSQL-backed persisted side-effect proof; retained read-path proof; production source/static caller proof; governance deferral for R6 |

## 1. Scope

This record covers local trusted evidence for policy/legal request ownership in
WS02-04B2A2B3. The pass proves that generic policy-document and
policy-acceptance mutation bodies are retired and cannot be used as authority
for legal content, policy lifecycle fields, acceptance actor, acceptance time,
IP address, or user-agent metadata.

The pass preserves controlled internal setup/service primitives and current
read paths. It does not create a policy editor, legal publishing process,
privacy-retention process, product acceptance workflow, browser proof,
provider/runtime evidence, ordinary JSON byte-limit closure, or HTTP/OpenAPI
tombstone representation closure.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04B2A2B3-R1` | Generic policy-document POST/PATCH mutations remain admin-gated, bodyless, non-mutating 410 tombstones. | pytest with route, HTTP, and PostgreSQL side-effect proof |
| `WS02-04B2A2B3-R2` | Generic policy-acceptance POST/PATCH mutations remain admin-gated, bodyless, non-mutating 410 tombstones. | pytest with route, HTTP, and PostgreSQL side-effect proof |
| `WS02-04B2A2B3-R3` | Controlled internal setup and retained reads remain available without reclassifying retired writes as active body-owned APIs. | pytest with service/setup and read-path proof |
| `WS02-04B2A2B3-R4` | Current frontend/source callers and seed guidance do not depend on retired policy/legal write bodies. | pytest/source-static |
| `WS02-04B2A2B3-R5` | B3 does not introduce a policy/legal request-body limit class or numeric threshold, and tombstones remain outside ordinary JSON body-route selection. | pytest with route/app metadata and source-static proof |
| `WS02-04B2A2B3-R6` | Later-owner legal/privacy/runtime/provider/request/response evidence remains outside B3. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1 | Generic policy-document writes are retained only as bodyless admin-gated 410 tombstones. | A POST/PATCH body, manual JSON parser, DB dependency, service call, alias, or active caller revives generic legal-content authoring. | Legal text, URLs, versions, active state, or lifecycle fields could become caller-owned. | Route-table, HTTP, source, and persisted no-side-effect tests. | workflow/route/PostgreSQL |
| R2 | Generic policy-acceptance writes are retained only as bodyless admin-gated 410 tombstones. | A POST/PATCH body, manual JSON parser, DB dependency, service call, alias, or active caller revives caller-owned acceptance evidence. | A caller could fabricate acceptance actor, policy version, timestamp, IP address, or user-agent evidence. | Route-table, HTTP, source, and persisted no-side-effect tests. | workflow/route/PostgreSQL |
| R3 | Internal setup/service primitives and retained reads are preserved without becoming public/admin write authority. | Tests accidentally prove only rejection and break legitimate setup/read paths. | Future passes lose honest setup evidence or policy/legal reads. | Controlled service creation and public/admin read-path tests. | workflow/service/read |
| R4 | Current callers and seed guidance avoid retired generic policy/legal write bodies. | Frontend or operator guidance keeps stale POST/PATCH workflows alive. | Future cleanup could be blocked by hidden dependencies. | Production source/static caller and seed-script checks. | workflow/source |
| R5 | Policy/legal tombstones do not require special body-limit classes or numeric thresholds. | B3 invents a large legal-text/URL/evidence limit or reclassifies tombstones as ordinary body routes. | Request-size authority would be split from the approved WS02-04 owners. | App metadata and source-static checks. | workflow/app/source |
| R6 | Later-owner work remains explicit and non-executable in B3. | B3 overclaims legal compliance, privacy retention, HTTP representation, browser/runtime, or provider closure. | Production-readiness status becomes dishonest. | Deferred declaration and explicit testing-record boundary. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | active admin, rejected/non-admin caller, public reader | covered | Tombstones are admin-gated; public policy-document reads and admin acceptance reads remain preserved. |
| States / lifecycle | retired write route, retained read route, active/inactive/retired/future policy document | covered | These states define the local B3 request-ownership boundary. |
| Actions | POST/PATCH generic writes, GET retained reads, controlled internal setup | covered | These are the frozen policy/legal surfaces in this pass. |
| Inputs / boundaries | no body, JSON body, malformed JSON, legal content, content URL, acceptance actor/time/IP/user-agent | covered | Tests prove these bodies do not become caller-owned write authority. |
| Time | already-effective, future-effective, retired policy documents | covered where applicable | Read eligibility depends on current policy-document lifecycle predicates. |
| Dependencies | FastAPI route table, TestClient, PostgreSQL, service/setup primitives, frontend/source files | covered | These are honest local proof layers for B3. |
| Concurrency / idempotency | no stateful B3 mutation path | not applicable | Generic writes are tombstones; genuine workflow acceptance remains later-owner work. |
| Authorization / privacy / security | active-admin dependency and rejected caller behavior | covered in scope | Tests prove auth order without claiming WS02-05A response representation. |
| Persistence / rollback | rejected POST/PATCH attempts must not create or mutate rows | covered | PostgreSQL tests prove prohibited side effects did not occur. |
| Recovery | stale callers receive compatibility tombstones | covered | HTTP 410 behavior is tested without owning exact representation. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Authenticated tombstone call without a body. | HTTP 410 lifecycle proof. |
| empty | yes | Bodyless tombstones and controlled setup defaults. | Covered by no-body and setup tests. |
| corrupt | yes | Malformed JSON sent to retired routes. | HTTP proof shows parsing/validation is not revived. |
| exceed | no | Numeric body limits are not B3-owned. | Deferred to WS02-04B2A1 / WS02-04B2A2C. |
| duplicate | yes | Duplicate or slash-alias route registrations. | Route-table negative-space proof. |
| delay | yes | Future-effective and retired policy-document read eligibility. | Public read-path proof. |
| reorder | no | No ordered operation sequence in scope. | Not applicable. |
| interrupt | yes | Rejected create/update attempts must not persist partial rows or field changes. | PostgreSQL side-effect proof. |
| race | no | No B3 mutable workflow to race. | Deferred outside B3. |
| expire / revoke | partial | Retired/future/inactive policy reads. | Public read-path proof only. |
| tamper | yes | Submitted legal content and acceptance metadata sent to retired writes. | HTTP and persisted side-effect proof. |
| retry | no | Tombstones have no persisted effect. | Not applicable. |
| recover | yes | Stale callers hit retained 410 tombstones. | HTTP lifecycle proof. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1 | Policy-document POST/PATCH route registration, auth order, no body, no parser, no DB, no mutation service, 410 behavior, and rejected no-side-effect writes. | FastAPI route table, TestClient, source inspection, PostgreSQL | `test_policy_document_request_ownership_contract.py` | Enough for local request-ownership and no persisted write effect; not exact tombstone representation or legal publishing proof. |
| R2 | Policy-acceptance POST/PATCH route registration, auth order, no body, no parser, no DB, no mutation service, 410 behavior, and rejected no-side-effect writes. | FastAPI route table, TestClient, source inspection, PostgreSQL | `test_policy_acceptance_request_ownership_contract.py` | Enough for local acceptance-evidence ownership; not a durable product acceptance workflow. |
| R3 | Internal service/setup creation and retained policy-document public reads / policy-acceptance admin reads. | Service/setup and TestClient read proof | `test_policy_document_request_ownership_contract.py`, `test_policy_acceptance_request_ownership_contract.py` | Enough to prove preserved local read/setup paths; not response minimization beyond current read availability. |
| R4 | Current frontend source and seed guidance avoid retired policy/legal HTTP write bodies. | Source/static | `test_policy_legal_caller_negative_space_contract.py` | Enough for current caller compatibility; not browser or deployed runtime evidence. |
| R5 | No alternate active routes, duplicate aliases, ordinary body-route classification, or B3-specific body-limit class. | Route/app metadata and source/static | `test_policy_legal_caller_negative_space_contract.py` | Enough to keep B3 within request-body ownership boundaries; not whole-request byte-limit closure. |
| R6 | Later-owner non-closure. | Governance declaration | Requirement JSON and this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Route metadata and HTTP behavior are both tested, so B3 is not relying only
  on static text.
- Submitted-body and malformed-body negative cases are covered for all four
  tombstone routes.
- Successful setup/read proof uses controlled internal service primitives and
  retained public/admin read paths.
- Rejected POST/PATCH scenarios prove prohibited persisted side effects did not
  occur where policy-document or policy-acceptance rows could otherwise be
  created or changed.
- Caller and script negative-space tests cover current production frontend
  source and local seed guidance without forbidding harmless retained GET/read
  integration.
- Time-boundary proof is limited to policy-document public read eligibility;
  no expiry/retention process is claimed.
- Genuine PostgreSQL race/concurrency behavior, provider behavior, browser
  behavior, deployed runtime behavior, legal-compliance approval, and
  privacy-retention evidence are not claimed by this pass.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Generic policy-document POST/PATCH | Authenticated stale callers receive lifecycle HTTP 410. | No request-body binding, manual body parsing, DB/session use, create/update service call, or persisted policy-document creation/update. | No persisted effect; idempotency not applicable. |
| Generic policy-acceptance POST/PATCH | Authenticated stale callers receive lifecycle HTTP 410. | No request-body binding, manual body parsing, DB/session use, create/update service call, or persisted policy-acceptance creation/update. | No persisted effect; idempotency not applicable. |
| Policy-document internal setup | Synthetic records can be created through controlled internal primitives. | Setup proof must not be treated as public/admin HTTP authoring. | Normal service transaction behavior. |
| Policy-document public reads | Active, non-retired, already-effective policy documents remain readable. | Inactive, retired, and future-effective documents are not public-eligible. | Read-only. |
| Policy-acceptance internal setup and admin reads | Synthetic records can be created internally and retrieved by active admin list/detail reads. | Rejected/non-admin callers cannot use admin read surfaces. | Read-only after setup. |
| Caller/source compatibility | Current callers and seed guidance do not use retired write bodies. | No hidden frontend or local seed dependency on generic write APIs. | Static proof only. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04B2A2B3-R6` | deferred | Booking-policy acceptance lifecycle, ordinary JSON byte limits, HTTP/media/OpenAPI/cache/tombstone representation, broad request ownership, response minimization, identity/account authority, final legal/privacy/retention policy, product acceptance workflows, external ingress limits, and provider/runtime evidence remain with their owners and cannot be closed by local B3 request-ownership evidence. | Listed downstream owners |
| Booking-policy acceptance lifecycle | covered elsewhere | B2A2B1 owns route lifecycle for booking-policy acceptance tombstones; B3 does not absorb that scope. | `WS02-04B2A2B1` |
| Ordinary JSON and special request-body limits | covered elsewhere | B3 proves no policy/legal-specific limit is introduced. | `WS02-04B2A1`, `WS02-04B2A2C` |
| HTTP media, OpenAPI, cache, and tombstone representation | covered elsewhere | B3 asserts only lifecycle 410 and bodyless shape. | `WS02-05A` |
| Response minimization | covered elsewhere | B3 preserves reads but does not close field minimization. | `WS02-05B2` |
| Legal text approval, privacy retention, account/legal processes | deferred | Local request-ownership tests cannot prove legal or privacy governance. | Legal/privacy/WS10 owners |
| Browser/deployed/provider/runtime proof | deferred | Local pytest cannot honestly prove deployed runtime or provider state. | Runtime/provider owners |

## 9. Adequacy Conclusion

This evidence is adequate for Gate B when focused B3 pytest, adjacent trusted
regressions, full trusted backend regression, checker regression, checker
domain/suite scopes, generated traceability, syntax/compile validation, and
diff/integrity checks pass.

Requirements R1 through R5 have executable trusted evidence. R6 is
intentionally deferred with zero pytest mappings. Checker `PASS` is structural
compliance evidence only; this record supplies the human adequacy boundary and
keeps legal/privacy/runtime/provider gaps explicit.
