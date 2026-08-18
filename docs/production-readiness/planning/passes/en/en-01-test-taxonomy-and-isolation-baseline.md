# EN-01 Test Taxonomy And Isolation Baseline

## Purpose

EN-01 establishes the production-readiness testing foundation for Pickup Lane.
It defines the test taxonomy, backend ownership model, traceability model,
checker responsibilities, database and network isolation baseline, fixture
rules, retry/flake/artifact policy, required foundation self-tests, and the
boundaries between EN-01 and later testing work.

EN-01 is a test-infrastructure and planning pass. It does not implement broad
application coverage, production behavior changes, provider suites, migration
rehearsals, release gates, or production-readiness sign-off.

## Authority And Control Mapping

EN-01 advances the foundation for these authoritative controls:

| Control | EN-01 role |
|---|---|
| `TST-001` | Define explicit test taxonomy, ownership vocabulary, and discovery expectations. |
| `TST-003` | Define browser-test taxonomy, quality rules, isolation expectations, and artifact/flake expectations without completing broad Playwright coverage. |
| `TST-004` | Define explicit execution-suite separation between ordinary deterministic tests, full-stack tests, and provider-contract tests. |
| `TST-010` | Establish synthetic-data, database, cleanup, order-independence, and network/provider isolation foundations. |
| `TST-011` | Apply the approved retry, flake, artifact, and risk-based coverage policy from `FDN-05`. |

EN-01 establishes foundations for these controls. It does not formally close
the broader testing controls that require later application, runtime, provider,
CI, repository-setting, operational, or release evidence.

The approved `FDN-05` policy remains authoritative for retries, flaky tests,
failure artifacts, and risk-based coverage. EN-01 must not invent a new owner
policy or replace that decision.

## Starting Assumptions

For production-readiness purposes, Pickup Lane starts from:

```text
ZERO TRUSTED BACKEND APPLICATION TEST COVERAGE
```

Existing backend application tests:

- do not define expected production-readiness behavior;
- do not constrain the final testing architecture;
- do not count as trusted production-readiness coverage;
- must not be used as EN-01 pilot evidence.

Future trusted application tests must be derived from authoritative production
requirements under the final testing system. EN-01 itself is validated through
testing-foundation, checker, and infrastructure self-tests, not arbitrary
application-domain pilot tests.

Historical/out-of-scope tests are not current production-readiness evidence and
are not inputs to current test design.

## Scope

EN-01 must define and prepare the foundation for:

- current-test taxonomy and ownership vocabulary;
- backend test organization direction;
- test layer selection rules;
- browser-test quality rules;
- execution-suite separation rules;
- stable requirement traceability;
- checker scope and result semantics;
- machine-readable metadata boundaries;
- human-readable scenario and risk reasoning;
- dedicated test database safety;
- database cleanup and isolation foundations;
- network and provider isolation foundations;
- fixture and support ownership;
- retry, flake, and artifact policy application;
- foundation self-tests and completion criteria.

EN-01 may build reusable infrastructure that later passes use. It must not
claim completion of later controls merely because the foundation can support
them.

## Non-Goals

EN-01 does not:

- create broad trusted application coverage;
- repair existing application-test areas;
- mine historical/out-of-scope tests;
- migrate all application tests;
- inventory every backend requirement;
- finish all backend coverage;
- complete provider sandbox or emulator suites;
- complete broad migration testing;
- complete broad concurrency coverage;
- complete browser or end-to-end coverage;
- complete full CI or release-gate enforcement;
- complete mutation hardening;
- close controls that require later runtime, provider, operational, CI,
  repository-setting, or release evidence;
- modify production application behavior merely to support the test framework.

## EN-01 Requirement Set

| ID | Source | Requirement |
|---|---|---|
| `EN01-R1` | `TST-001`, `TST-003` | Define the backend/testing taxonomy, ownership vocabulary, and browser-test quality foundation. |
| `EN01-R2` | `TST-001`, `TST-004` | Define the long-term backend test ownership architecture and execution-suite separation model. |
| `EN01-R3` | `TST-010` | Preserve strong dedicated PostgreSQL test database protection. |
| `EN01-R4` | `TST-010` | Preserve database cleanup and isolation foundations. |
| `EN01-R5` | `TST-004`, `TST-010` | Prevent uncontrolled real external provider calls in ordinary backend tests. |
| `EN01-R6` | `TST-010` | Require synthetic non-production test data and resources. |
| `EN01-R7` | `TST-011`, `FDN-05` | Apply approved retry, flake, artifact, and risk-based coverage rules. |
| `EN01-R8` | `TST-001`, `GOV-005` foundation | Establish pass-to-requirement-to-test traceability. |
| `EN01-R9` | Master blueprint EN-01 proof | Require foundation/checker self-tests. |
| `EN01-R10` | Evidence integrity | Enforce the zero-trust application-coverage starting point. |
| `EN01-R11` | `TST` foundation and authority integrity | Define checker result states as machine-verifiable compliance outcomes only. |

## Test Taxonomy

The production-readiness taxonomy must distinguish these categories:

- unit or policy tests;
- component or service tests;
- API integration tests;
- PostgreSQL integration tests;
- browser tests;
- provider integration tests;
- migration tests;
- concurrency tests;
- security tests;
- smoke tests.

The taxonomy defines language, ownership, isolation expectations, and later
suite boundaries. It does not mean every category receives complete suites
during EN-01.

## Browser Testing Quality Foundation

Browser tests created by later coverage work must follow stable quality rules:

- use semantic and stable locators rather than brittle positional selectors
  where possible;
- create deterministic test state;
- control time when behavior depends on time;
- avoid arbitrary sleep-based synchronization;
- define explicit failure-artifact behavior;
- sanitize failure artifacts;
- preserve deterministic isolation and cleanup expectations.

EN-01 defines these browser-test quality rules and taxonomy expectations. It
does not create broad Playwright, browser, or end-to-end coverage.

## Backend Ownership Architecture

The intended long-term backend organization is domain-first:

```text
backend/tests/
  domains/
  workflows/
  platform/
  migrations/
  provider_contract/
  support/
  checker/
```

Ownership rules:

- `domains/` owns stable business and domain invariants.
- `workflows/` owns genuine cross-domain orchestration or user-flow behavior
  whose integration is itself the contract.
- `platform/` owns intentionally global backend, API, framework, and security
  behavior.
- `migrations/` owns Alembic and schema-history testing.
- `provider_contract/` owns explicitly separated real provider, emulator,
  sandbox, or test-resource verification.
- `support/` owns reusable testing infrastructure only.
- `checker/` owns checker/compliance self-tests and supporting checker test
  infrastructure.

Technical test type must not be the primary top-level ownership structure.
Test type may be expressed through filenames, markers, metadata, or execution
configuration where useful.

## Test Layer Rules

Test a rule at the lowest reliable layer that can actually prove the invariant.

Examples:

- pure policy or calculation behavior belongs in unit/policy tests;
- transactional domain behavior belongs in service/domain/PostgreSQL tests;
- HTTP parsing, status, headers, and auth wiring belong in FastAPI API tests;
- PostgreSQL constraints, locking, and isolation belong in real PostgreSQL
  tests;
- genuine races require independent PostgreSQL sessions or connections;
- provider contracts require explicit provider sandbox, emulator, or test
  resources;
- migration-history behavior belongs in the migration suite.

Duplicate coverage across layers is useful only when the second layer protects
a distinct failure mode. Do not copy every scenario into every layer.

## Execution Suite Separation

The testing architecture must distinguish execution environments and provider
access explicitly.

Ordinary or mocked deterministic tests:

- make no uncontrolled external provider calls;
- replace provider boundaries with fakes, mocks, overrides, or equivalent local
  substitutes;
- form the normal trusted local and CI suite.

Full-stack tests:

- use real application stack components only where explicitly required;
- remain isolated from production resources;
- run in a clearly separated execution environment.

Provider-integration or provider-contract tests:

- use Firebase emulator, Stripe test mode, R2 test resources, or equivalent
  sandbox/test resources;
- opt into only the required network and provider access;
- use isolated test credentials and resources;
- never use production resources.

Browser testing may participate in mocked or full-stack execution depending on
the suite. Those execution environments must remain distinguishable. EN-01
defines the separation rules but does not claim the later suites are fully
implemented.

## Requirement And Pass Traceability

The permanent traceability model is:

```text
PRODUCTION-READINESS PASS
  -> STABLE REQUIREMENT ID
    -> MEANINGFUL SCENARIOS / EDGE CASES
      -> PYTEST TESTS
```

Stable requirement IDs are the permanent bridge between production-readiness
passes, test intent, and implementation evidence. Exact Python test names are
not permanent pass documentation.

Permanent traceability ownership is split across four layers.

The canonical pass planning document owns:

```text
PASS
  -> REQUIREMENT IDs
```

It records the stable requirements the pass introduces, owns, or advances; the
authoritative source or control; requirement meaning; explicit scope and
non-goals; and blocked, deferred, covered-elsewhere, or not-applicable
decisions where relevant. It must not maintain fragile exact pytest node IDs.

The owning testing/risk record for each coherent domain, workflow, or platform
testing scope owns:

```text
REQUIREMENT ID
  -> MEANINGFUL SCENARIOS / EDGE CASES / RISKS
```

It records useful human reasoning such as invariants, important risks,
meaningful actor/state/boundary/failure cases, correct owning layer, and
accepted gaps, blockers, deferrals, or covered-elsewhere decisions with
reasons. It must not duplicate every Python test or recreate the product
specification.

Pytest metadata owns:

```text
REQUIREMENT ID
  -> EXECUTABLE TEST EVIDENCE
```

Pytest tests declare the stable requirement IDs they prove. One requirement may
map to many tests, and one test may legitimately prove multiple requirements.

Generated traceability output owns:

```text
PASS
  -> REQUIREMENT
    -> CURRENT EXACT PYTEST NODE IDs
```

Tooling or pytest collection generates exact current pytest node references.
This output is derived, not manually maintained permanent documentation.
Renaming or moving a test therefore does not break permanent pass traceability.

Supported requirement states should include, where appropriate:

- `covered`;
- `partial`;
- `missing`;
- `blocked`;
- `covered_elsewhere`;
- `not_applicable`;
- `deferred`.

`covered_elsewhere`, `not_applicable`, `blocked`, and `deferred` require a
reason. The final system must not create giant duplicated requirement/test
registries.

## Canonical Requirement Declarations

Each stable requirement ID must have one canonical declaration. That
declaration contains only the minimum authoritative identity needed by tooling,
such as:

- requirement ID;
- authoritative source or control reference;
- owning scope or pass where applicable;
- current required, blocked, deferred, covered-elsewhere, not-applicable, or
  similar state where machine enforcement needs it.

The checker validates pytest requirement metadata against canonical
declarations. The canonical declaration source must support deterministic
machine parsing, uniqueness, stable IDs, generated test mapping, and minimal
duplication. Markdown prose alone must not be scraped heuristically to
determine requirement identity.

The exact implementation and serialization format is an engineering decision
for EN-01 implementation, provided it preserves those constraints. The
canonical declaration source must not become a second product specification and
must not require expected effects, every edge case, exact test names, or
duplicated prose in the machine registry.

## Scenario And Edge-Case Discovery

EN-01 preserves this human reasoning flow:

```text
AUTHORITY
  -> INVARIANT
    -> RISK
      -> ACTOR / STATE / ACTION / INPUT / TIME / DEPENDENCY ANALYSIS
        -> EQUIVALENCE CLASSES / BOUNDARIES
          -> SAFEGUARD
            -> CORRECT OWNING TEST LAYER
              -> EXPLICIT GAP IF UNRESOLVED
```

Useful failure transformations include:

- omit;
- empty;
- corrupt;
- exceed;
- duplicate;
- delay;
- reorder;
- interrupt;
- race;
- expire;
- revoke;
- tamper;
- retry;
- recover.

Do not require blind Cartesian-product enumeration. Meaningful edge cases
should correspond to distinct risks, rules, or safeguards. Human review remains
responsible for deciding whether scenario discovery and oracles are adequate.

## Checker Responsibility

The custom checker is a compliance verifier. It should focus on
machine-verifiable rules such as:

- target validity;
- pytest collection and discovery;
- requirement-ID syntax;
- requirement-ID uniqueness;
- missing or orphan requirement mappings;
- small manifest schema where manifests exist;
- explicit unresolved blockers or gaps;
- DB environment safety;
- network and provider safety configuration;
- marker and config invariants;
- historical/out-of-scope test exclusion;
- suite and repository invariants;
- obvious mechanically provable prohibited constructs.

The checker must not claim to mechanically prove:

- product intent;
- complete scenario discovery;
- semantic test quality;
- correct ambiguous domain ownership;
- adequacy of every oracle;
- behavioral completeness.

Uncertain static heuristic findings must not be elevated into false semantic
certainty.

## Checker Scopes

The intended checker architecture should support:

| Scope | Purpose | Completeness claim |
|---|---|---|
| File | Quick validation of one test file. | No completeness claim. |
| Domain or subtree | Validation of one coherent owned test area, local mappings, local manifests, and scoped gaps. | Scoped machine-compliance only. |
| Suite | Global uniqueness, orphan checks, discovery rules, configuration, environment/network policies, and repository-wide invariants. | Suite-level machine-compliance only. |

File scope supports quick local validation only. Domain, subtree, and suite
scopes are required for scoped and global machine-compliance checks.

## Checker Result Semantics

Checker result states must have these meanings:

| State | Meaning |
|---|---|
| `PASS` | The requested scope satisfies all applicable machine-verifiable Pickup Lane test-compliance rules, and required declared machine-readable evidence is internally consistent. It does not imply semantic completeness or adequate testing. |
| `FAIL` | One or more definite machine-verifiable compliance violations exist. |
| `BLOCKED` | Required authoritative information, required declared evidence, or another prerequisite needed to evaluate the scope is missing, unresolved, or explicitly blocked. This is not equivalent to a test assertion failure. |
| `USAGE_ERROR` | The checker invocation, arguments, target, or requested mode is invalid. |
| `INTERNAL_ERROR` | The checker itself malfunctioned or encountered an unexpected internal failure. |

No checker result state replaces human adequacy review or later runtime,
provider, CI, operational, or release evidence.

## Machine-Readable Metadata Model

Machine-readable metadata exists to support deterministic compliance checks
with minimal duplication. The metadata architecture is:

- canonical stable requirement declarations;
- pytest-associated requirement metadata;
- generated exact test references;
- small machine-readable manifests only where they provide unique
  machine-verifiable value.

Potentially useful machine-readable data includes:

- requirement IDs;
- authoritative source references;
- critical or required requirement lists;
- explicit blockers and gaps;
- finite state matrices where machine extraction and comparison provide real
  value;
- suite and environment classification.

Do not duplicate every scenario, effect, prohibited effect, time boundary, test
function name, source-review narrative, ownership explanation, assertion, or
product requirement in machine-readable metadata. The exact serialization
format is an implementation detail unless an authority requires one.

## Human-Readable Testing Evidence

Permanent human-readable testing records are organized by coherent owned
testing scope, not necessarily every individual test file. They should be
concise and explain:

- authoritative requirements used;
- invariant and risk reasoning;
- selected scenarios and edge cases;
- why each selected test layer is the correct owner;
- accepted gaps, blocked work, deferrals, and covered-elsewhere decisions;
- human review conclusions about adequacy.

They may group equivalent scenarios. They are not required to repeat test
implementation details, repeat authoritative product specifications, or remain
manually synchronized with exact pytest filenames or node IDs. Generated
tooling handles exact test-reference mapping.

A scope may be considered adequately tested for its current declared
requirements and risk model only when, as applicable:

- authoritative requirements are finalized;
- meaningful requirements have traceable tests;
- relevant states, roles, and lifecycle values have been reviewed;
- success effects are proven;
- prohibited effects on rejected or failing operations are proven;
- relevant boundaries are tested;
- relevant authorization and privacy behavior is tested;
- relevant PostgreSQL guarantees are proven on PostgreSQL;
- relevant concurrency and idempotency behavior is tested;
- relevant provider boundaries are covered at the correct layer;
- confirmed bugs have regression tests;
- gaps are explicit;
- required automated validation is green;
- human review agrees that scenarios and oracles are adequate.

Checker PASS alone does not establish adequate testing.

## Test DB And Isolation Foundation

Standard backend tests must preserve strong PostgreSQL test database protection.
The dedicated serial local test database name is:

```text
pickup_lane_test_db
```

That exact database name must remain protected as the dedicated serial local
test database unless or until a stronger explicitly approved worker-isolation
naming model is introduced. A database is not safe merely because its name
contains `test`. Production, staging, development, backup, and similarly named
databases must be rejected before cleanup or test execution.

EN-01 must include wrong-DB rejection evidence and must not weaken existing
production, staging, or development database protections.

Tests must be isolated and order-independent. Preserve:

- cleanup before and after tests where required by the EN-01 foundation;
- dependency override cleanup;
- schema and table cleanup completeness checks;
- failure-safe cleanup behavior.

Future architecture may include:

- per-worker PostgreSQL databases;
- transaction/savepoint isolation for compatible ordinary tests;
- a separate committed-state lane;
- an independent-session concurrency lane;
- metadata or PostgreSQL introspection-driven cleanup validation.

EN-01 does not have to complete every future parallelism or isolation
optimization. It must preserve or improve existing safety while preparing for
that direction.

## Network And Provider Safety

Ordinary backend tests must not make uncontrolled real external provider calls.

The foundation model is:

1. dependency injection or fakes at application boundaries;
2. process-level network blocking;
3. CI and environment isolation;
4. separate explicit provider-contract suites.

Provider-contract suites must follow the execution-suite separation rules.

EN-01 owns the default safety and separation foundation. It does not claim that
Firebase, Stripe, R2, email, or other provider-contract suites are complete.

## Synthetic Data

Backend tests must use synthetic non-production data and resources. Production
users, payment resources, credentials, objects, messages, provider resources,
or copied production datasets must not be normal test fixtures.

## Fixtures And Support

Root `conftest.py` owns universal test infrastructure only:

- environment safety;
- DB, session, and client foundation;
- global dependency cleanup;
- global network safety where appropriate.

Domain or workflow-local `conftest.py` files own reusable local setup for that
owned area only.

`support/` owns reusable infrastructure and helpers with explicit
responsibilities. It must not become a miscellaneous dumping ground, and
helpers must earn their indirection.

Scenario-specific setup should remain visible in tests when hiding it would
reduce clarity.

## Retry, Flake, And Artifact Rules

Approved `FDN-05` rules apply:

- retries are diagnostic aids and cannot silently hide a recurring failure;
- deterministic unit, service, API, database, and concurrency tests do not
  depend on retries for success;
- a diagnostic retry is allowed only when the first failure remains visible and
  gate behavior is explicit;
- flaky behavior requires an owner, defect reference, reason, containment, and
  expiry or review condition;
- quarantine cannot remove critical-workflow coverage without an approved
  replacement;
- failure artifacts must be useful, sanitized, access-controlled, and free of
  secrets or sensitive user, message, and payment data;
- coverage is risk-based, not governed by one universal percentage;
- recurring failures require root-cause work.

Artifact retention duration remains a later evidence-based value. EN-01 must
not invent it.

## Runtime Authority

Pytest owns test runtime behavior. The custom checker should not be designed as
a second general pytest runtime authority.

Useful assertion and helper concepts may remain in pytest infrastructure.
Runtime evidence should primarily come from pytest execution, test assertions,
normal pytest or JUnit artifacts, and explicitly required environment,
provider, or runtime evidence rather than a parallel semantic evidence system.

## Mutation Testing

Mutation testing is not part of normal checker PASS and is not a universal
EN-01 completion requirement.

Mutation testing may be used later as optional targeted hardening for high-risk
logic such as authorization, money, idempotency, capacity, lifecycle
transitions, and small critical policy functions.

## CI Responsibility And Scope Boundary

EN-01 may define expected CI integration points:

- static quality checks;
- compliance checker validation;
- migration validation;
- trusted pytest runtime suites;
- separate provider or hardening jobs where appropriate.

EN-01 establishes the testing foundation and expected integration points only.
Broader CI enforcement, artifact retention, release evidence, branch
protection, scan policy, and release gating remain owned by later controls and
passes.

## Later-Scope Boundaries

Later work owns:

- complete backend inventory;
- broad application coverage expansion;
- full CI execution and enforcement;
- provider integration suites;
- broad migration tests;
- runtime and staging verification;
- broad concurrency coverage;
- browser and end-to-end coverage;
- later flaky-test enforcement and retention mechanisms;
- optional mutation hardening.

EN-01 may build reusable foundations for these areas. It must not claim their
completion.

## EN-01 Self-Test Requirements

EN-01 implementation must include foundation/checker self-tests proving at
least:

- suite and category discovery behavior;
- checker target and scope behavior;
- canonical requirement declaration, requirement metadata, and traceability
  behavior;
- wrong test-DB rejection;
- database cleanup safeguards;
- network guard behavior;
- execution-suite separation invariants;
- browser quality rules where machine-checkable at the foundation level;
- dependency override cleanup;
- artifact sanitization behavior required at this foundation level;
- retry/flake policy behavior required at this foundation level;
- historical/out-of-scope tests cannot count as current evidence;
- relevant configuration invariants;
- all checker result states.

EN-01 must not require arbitrary application-domain pilot tests.

## Definition Of EN-01 Completion

EN-01 implementation is complete only when the foundation itself proves:

- taxonomy and configuration are coherent;
- checker scopes and metadata rules behave as designed;
- canonical requirement declarations are enforced;
- requirement traceability works;
- wrong DB configuration is rejected;
- cleanup safeguards work;
- network and provider default isolation works;
- dependency overrides do not leak;
- artifact and flake rules required at this foundation level are enforced and
  tested;
- historical/out-of-scope tests cannot count as current evidence;
- all checker result semantics are correct;
- documentation matches implementation;
- required EN-01 self-tests pass.

Application pilot coverage is not required for EN-01 completion.

## Stop Conditions And Unresolved Gaps

Implementation must stop rather than guess if:

- a higher-authority requirement conflicts with this plan;
- implementation would require stealing scope from another pass;
- a strong DB or network safety guarantee would need to be weakened;
- an owner, product, or risk decision unexpectedly appears;
- required evidence cannot be produced;
- implementation requires modifying unrelated production behavior;
- the final architecture cannot preserve or improve existing safety guarantees.

Unresolved gaps must be explicit. A gap may be `blocked`, `deferred`,
`covered_elsewhere`, or `not_applicable` only with a reason and, where
applicable, the owning later pass or evidence source.
