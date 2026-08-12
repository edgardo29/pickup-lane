# Release / Rollback Record Template

## 1. Purpose

Use this template for a completed release, rollback, or forward-fix record after
supporting evidence exists. The blank template is a repository-safe evidence
container. It is not itself proof that any deployment, rollback, or forward-fix
occurred.

## 2. Safe-Use And Confidentiality Rules

Blank fields are not evidence. Unknown or unavailable external facts must stay
identified as unresolved rather than filled with guessed values. An executed
record requires accepted supporting evidence for every material claim.

Never include credentials, passwords, API keys, tokens, private keys, database
credentials, webhook secrets, private or signed URLs, raw provider payloads,
personal or private user data, payment data, sensitive provider identifiers,
local filesystem paths, or local usernames.

Use only safe placeholders or sanitized evidence references.

## 3. Record Status

| Field | Value |
|---|---|
| Record state | `[draft / executed / reviewed / superseded]` |
| Environment | `[preview / staging / production / other approved environment]` |
| Record owner | `[role or accountable owner]` |
| Review state | `[pending / accepted / rejected / superseded]` |

## 4. Release Identity And Artifact References

| Field | Value |
|---|---|
| Immutable source revision | `[full approved source revision]` |
| Backend deployment or artifact identity | `[sanitized backend artifact reference]` |
| Related frontend deployment or artifact identity | `[sanitized frontend artifact reference or not applicable]` |
| Dependency lockfile identity | `[lockfile name and sanitized immutable reference]` |
| Release trigger and intended change | `[concise sanitized description]` |

## 5. Compatibility And Migration References

| Field | Value |
|---|---|
| Migration head or schema-compatibility reference | `[migration head, schema contract, or not applicable]` |
| Compatibility decision | `[compatible / incompatible / not applicable / unresolved]` |
| Prior rollback artifact identity | `[sanitized prior artifact reference or unavailable]` |

## 6. CI And Approval References

| Field | Value |
|---|---|
| CI result-set reference | `[sanitized CI run or artifact reference]` |
| Approval record | `[sanitized approval reference]` |
| Required checks reviewed | `[yes / no / unresolved]` |

## 7. Provider Deployment Linkage

| Field | Value |
|---|---|
| Provider deployment linkage | `[sanitized provider evidence reference or unavailable]` |
| Runtime configuration linkage | `[sanitized runtime evidence reference or unavailable]` |
| External provider facts unavailable | `[list unresolved facts or none]` |

Provider/runtime evidence remains later-owned until accepted evidence exists.
This template must not convert an unavailable provider fact into repository
proof.

## 8. Health / Readiness Validation

| Field | Value |
|---|---|
| Health/readiness validation | `[sanitized validation reference and outcome]` |
| Validation environment | `[approved environment]` |
| Observed readiness result | `[ready / not ready / unresolved]` |
| Observed liveness result | `[live / not live / unresolved]` |

## 9. Rollback Or Forward-Fix Decision

| Field | Value |
|---|---|
| Rollback trigger | `[trigger, not applicable, or unresolved]` |
| Rollback or forward-fix decision | `[rollback / forward-fix / no action / unresolved]` |
| Rollback/forward-fix procedure reference | `[sanitized runbook or procedure reference]` |
| Decision owner | `[role or accountable owner]` |

## 10. Observed Result

| Field | Value |
|---|---|
| Observed result | `[sanitized operational result]` |
| User-impact summary | `[sanitized summary or not applicable]` |
| Follow-up required | `[yes / no / unresolved]` |

## 11. Sanitized Evidence References

| Evidence Type | Sanitized Reference | Review State |
|---|---|---|
| Source/artifact | `[reference]` | `[pending / accepted / rejected]` |
| CI/checks | `[reference]` | `[pending / accepted / rejected]` |
| Provider/runtime | `[reference or unavailable]` | `[pending / accepted / rejected / external]` |
| Health/readiness | `[reference]` | `[pending / accepted / rejected]` |
| Rollback/forward-fix | `[reference or not applicable]` | `[pending / accepted / rejected / not applicable]` |

## 12. Unresolved Or Unavailable External Fields

| Field | Why It Is Unavailable | Later Owner / Evidence |
|---|---|---|
| `[external field]` | `[reason]` | `[later pass, provider evidence, or owner]` |

## 13. Completion / Review Acknowledgement

| Field | Value |
|---|---|
| Completed by | `[role or accountable owner]` |
| Reviewed by | `[role or accountable reviewer]` |
| Review conclusion | `[accepted / rejected / superseded / unresolved]` |
| Remaining gaps | `[none or explicit unresolved items]` |

An executed record is complete only when required fields are filled with
sanitized, accepted evidence or explicitly marked unavailable with a later
owner. The blank template remains non-evidence.
