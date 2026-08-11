# EN-01 Checker And Foundation Testing Record

## Scope

This record covers the EN-01 checker, requirement declaration, traceability,
environment-safety, suite-separation, browser-quality, retry/flake, and artifact
foundation. It does not cover application-domain behavior.

## Requirements And Risks

| Requirement | Invariant | Important Risk | Owning Layer | Current Evidence |
|---|---|---|---|---|
| `EN01-R1` | The test taxonomy and browser-quality foundation are explicit and machine-checkable where reliable. | Browser or suite labels become vague or brittle. | Checker policy and foundation tests. | Covered by checker foundation and browser-quality policy tests. |
| `EN01-R2` | Trusted test ownership is domain-first and execution suite type is explicit. | Existing untrusted app tests or provider tests become trusted ordinary evidence accidentally. | Checker targeting and suite policy. | Covered by target and suite-separation foundation tests. |
| `EN01-R3` | Backend tests only accept the exact dedicated PostgreSQL test database. | Cleanup or runtime tests touch development, staging, production, or deceptive test-like databases. | Pytest environment safety. | Covered by environment-safety tests. |
| `EN01-R4` | Cleanup inventory remains complete and cleanup is failure-safe. | New tables escape cleanup and leak state between tests. | Pytest environment safety. | Covered by cleanup-inventory tests. |
| `EN01-R5` | Ordinary tests cannot silently make uncontrolled provider/network calls. | Deterministic suites reach live providers or production resources. | Pytest network guard and checker policy. | Covered by network guard and suite policy tests. |
| `EN01-R6` | Test settings and resources are synthetic and non-production. | Tests rely on real credentials, provider state, or copied production data. | Pytest environment setup and checker policy. | Covered by environment and sensitive-content tests. |
| `EN01-R7` | Retry, flake, and artifact rules preserve failure visibility and sanitized evidence. | Retries hide defects or artifacts expose secrets. | Checker policy and artifact sanitizer. | Covered by retry-config and artifact sanitizer tests. |
| `EN01-R8` | Traceability is generated from canonical requirements and pytest metadata. | Manual node registries drift after test moves or renames. | Checker declaration/discovery/traceability modules. | Covered by generated traceability tests. |
| `EN01-R9` | EN-01 proves its own foundation instead of using application pilot tests. | Application tests are mistaken for EN-01 proof. | Checker self-tests. | Covered by EN-01 foundation tests only. |
| `EN01-R10` | Existing backend application tests are zero-trust production-readiness evidence. | `pages/`, `shared/`, or historical tests count toward trusted EN-01 evidence. | Checker targeting and trusted discovery. | Covered by untrusted-application and historical-exclusion tests. |
| `EN01-R11` | Checker states are machine-compliance outcomes only. | PASS is misread as semantic completeness or adequate testing. | Checker report and result-state tests. | Covered by result-state tests. |

## Adequacy Conclusion

EN-01 is adequately tested for the foundation scope when the checker self-tests,
environment-safety tests, artifact/browser policy tests, and representative
checker file/domain/suite runs pass locally. Human review remains responsible
for future application-domain scenario adequacy.
