# [Pass ID] — [Descriptive title]

[In one or two plain-English paragraphs, explain what this work will accomplish, why it matters, and what will be different when it is done. Assume the reader has not seen earlier conversations. Replace all bracketed guidance and instructions in this template with the actual plan.]

**Parent pass:** [Pass NN — official Production Launch Requirements name]  
**Executable unit:** [Whole parent, or child name and bounded outcome]  
**Assigned production-launch requirements:** [Exact requirement IDs]  
**Parent pass record:** [Link to `docs/production-readiness/pass-records/pass-NN.md`, including its Stage 0 scope decision]

A plan may be written in the parent pass record or in a document linked from it. Every executable unit needs a written, independently reviewed plan; a separate planning file is optional. A child plan covers its assigned work while the parent record retains ownership and coverage of the whole pass.

## 1. Purpose, scope, and starting point

[Establish enough context for a developer to understand the work before reading the design. Summarize the relevant user, system, or operational workflow in ordinary language.]

Describe what starts the workflow, how it currently works, and the specific result the unit must deliver. Identify the exact Production Launch Requirements owned here. Cite each controlling product specification or approved decision by file and section; confirm that it describes the current application and does not conflict with the Production Launch Requirements. Link to the parent record's Stage 0 assessment rather than copying its full requirement inventory.

Identify what current source, configuration, and verified evidence already establish. Distinguish observed behavior from an existing implementation that has not been verified against the Production Launch Requirements. State the remaining work and its prerequisites. Explain what the unit will add, change, or preserve; name affected interfaces or consumers and specific work outside its boundary. For a child, cite the parent record's ownership map and any upstream requirement on which it depends by exact ID.

If an essential fact or decision is missing, identify the precise question, its owner, and which work it blocks. Do not design around a guessed production service, business rule, provider setting, or limit. If only a final setting can wait, show that all conditions for that exception in Production Launch Requirements Section 3.3 apply.

## 2. Required results and safeguards

[Describe what the completed unit must do, independently of how it will be built. Organize by meaningful behavior or operational result; cite the exact requirement IDs without copying full Production Launch Requirements text.]

For each affected operation or materially different outcome, make clear:

- **When it applies:** The trigger, input, actor, starting state, or event.
- **Required result:** The observable behavior and any necessary change to data, permissions, configuration, or external state.
- **Prohibited result:** The side effect or unsafe outcome that must not occur.
- **Preserved behavior:** Existing behavior and interfaces that must continue to work.

Account for every applicable member of a fixed set of operations, statuses, provider outcomes, callers, or consumers. A successful example does not stand in for the other members. Group cases only when each member is named and truly has the same treatment; exclude unrelated cases with a brief reason. Describe authorization, privacy, financial, capacity, and data-integrity rules when they govern the result.

Before choosing a sensitive design covered by Production Launch Requirement P03.R09, identify where an untrusted caller or input reaches a protected operation, a plausible misuse, the prohibited effect, and the requirement and check that govern it. If a material misuse has no governing requirement, record the search and amendment decision and stop the affected design until the Production Launch Requirements are amended. Do not add requirements through this plan.

## 3. Chosen design or operational approach

[This is the main engineering section. Choose one coherent approach. Make it specific enough that another engineer can carry it out without inventing an important architectural or behavioral decision.]

Begin with an end-to-end explanation in plain English. Describe which existing parts participate, what each part owns, how information moves between them, and the order that produces the required result. For a non-code unit, explain the decision method, configuration procedure, operational exercise, or qualification path in the same concrete way.

Then add descriptive numbered subsections such as `### 3.1 [Design area]` and `### 3.2 [Design area]` for the actual work. Cover these matters where they affect correctness:

- Existing components, source files, configuration, and interfaces to change; responsibilities of any necessary new component.
- Inputs, outputs, data formats, validation, API behavior, and the source of important information.
- Ownership and lifetime of state or data: where it is stored, who may change it, and when it is cleared or retained.
- Order of calls and updates across the browser, API, database, jobs, and external services; transactions and state transitions where applicable.
- Authorization and privacy controls, trust boundaries, provider contracts, and relevant operational settings.
- Compatibility with existing callers, stored records, deployments, and unaffected workflows; migration or rollout order when needed.
- The concrete treatment of each affected operation, consumer, allowed value, or provider outcome. A shared helper does not prove every caller needs identical behavior.

Explain an important technical mechanism when it first appears: what it is, why this work needs it, how it operates here, and how it interacts with the rest of the design. Give exact rules after the plain-English explanation. Avoid a new table, route, job, service, abstraction, or setting unless an exact requirement or demonstrated correctness need justifies it. If replacing an existing path, identify the specific Production Launch Requirements Section 3.4 reason, its supporting evidence, and what is removed when the replacement takes over.

Resolve questions answerable from repository evidence. If a genuine owner or provider decision remains unresolved, state the exact decision and its effect on the plan; do not present a menu of unchosen designs as an implementation instruction.

## 4. Failures, boundaries, and simultaneous events

[Explain the abnormal paths that could change the result or violate a safeguard. Keep normal-flow details in Section 3; describe the additional response here. Omit cases that cannot affect this unit.]

For each realistic failure or overlap, identify:

- **Condition:** The exact invalid input, state change, timeout, provider result, interruption, or ordering of competing events.
- **Response:** What the system or operator does next, including any returned error or visible state and which data is retained, changed, or cleared.
- **Retry or recovery:** Whether work may be repeated, how an unknown outcome is reconciled, and how partial work is completed or reversed.
- **Safety check:** What must not happen, such as a duplicate charge, unauthorized read, stale result, lost audit entry, or partially completed transaction treated as success.

Consider invalid inputs, unavailable or malformed responses, provider failures and unknown outcomes, cancellations, repeated requests, simultaneous operations, changing permissions, and recovery after interruption when they are plausible for the chosen design. Where order changes the result, describe each material order. Do not add hypothetical failure combinations merely to fill this section. For non-code work, cover failed checks, unavailable settings, incomplete evidence, and recovery or escalation paths that matter to the required result.

## 5. Verification plan

[Plan the proof; do not report checks as passed here. Actual methods, observations, and evidence belong in the parent pass record or linked evidence.]

For each applicable requirement and numbered verification scenario, specify:

- **Reference and scenario:** Exact requirement and verification IDs, starting state, input or event, and any failure or simultaneous operation exercised.
- **Method and environment:** Existing test or procedure to reuse, new check needed, the layer or service where it runs, and the environment or release boundary it proves.
- **Expected observation:** The response, saved change, provider state, user-visible result, or operational result that establishes success.
- **Prohibited effects:** How each relevant forbidden outcome will be checked and what absence must be observed.
- **Proof limit:** What this method cannot establish and which later pass, selected service, or production setting must supply that evidence.

Cover materially different outcomes, failure paths, and preserved behavior. Choose the lowest reliable layer that proves the claim; a helper test alone does not prove its callers use it, and a build does not prove a runtime authorization rule. Use controlled, isolated resources for active failure and concurrency checks and respect the Production Launch Requirements' production-safety boundaries. Before the Pass 03 verification map exists, plan verification directly against the Production Launch Requirements and verification scenarios. Once the map is established, ensure subsequent plans remain consistent with it. Planned verification must never be treated as completed evidence.

## 6. Finish line and handoffs

[State what must be true for this executable unit to finish, without reproducing the parent's full Production Launch Requirements completion condition or adding a second gate checklist.]

Identify the delivered result, safeguards, compatibility, and verification due now. Point to the parent pass completion condition and explain how this unit contributes to it. A child finishing does not by itself complete its parent.

For each permitted later obligation, state the exact requirement, missing prerequisite, receiving pass or owner, event that makes it executable, required result, and latest completion boundary. Link to the obligation in the parent record and name the handoff. Distinguish a later check expressly allowed by the Production Launch Requirements from an unresolved prerequisite that prevents this unit's design or result from being completed. Leave any unfinished obligation visibly unfinished; do not claim completion from an unrun check.

---

**Author self-check — remove before submitting a completed plan**

- Can a developer new to this work explain the existing workflow, intended outcome, chosen approach, and why each important mechanism is needed?
- Does the plan account for every assigned requirement, affected operation, material state or outcome, existing caller, and prohibited effect without copying the Production Launch Requirements?
- Are the normal flow, realistic failure and overlap paths, recovery behavior, and compatibility rules concrete enough to implement without guessing?
- Can each planned check observe its required result and relevant prohibited effects in the stated environment, with later evidence and blockers assigned precisely?
- Is each new component or changed interface justified by a current requirement or demonstrated need, and is the plan proportional to this unit's complexity?
