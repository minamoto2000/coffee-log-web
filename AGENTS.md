# coffee-log-web Development Handoff

## Scope

Use this repository (`minamoto2000/coffee-log-web`) as the source of truth for implementation status.

Implementation status must be judged from the repository's actual code, tests, templates, README, and directory structure. Do not infer completed work from plans or specifications alone.

## Current objective

Make `coffee-log-web` submission-ready for job applications.

Do not expand the product beyond the Current MVP. The priority is to make the existing MVP contract correct, tested, demonstrable, and reproducible.

## Priority order

1. Align MVP API contracts.
2. Complete domain invariants and datetime handling.
3. Add tests for the MVP acceptance criteria.
4. Complete the Core Vertical Slice Jinja pages.
5. Clean the repository and finalize the public README.
6. Run the final submission acceptance check from a clean environment.

Work through this order. Do not start lower-priority polish while a higher-priority correctness item remains open.

## Current task

Start with MVP API contract alignment.

Required work includes:

- make `POST /logs` return the specified nested BrewLog + Evaluation response
- add `GET /logs/{brew_log_id}/evaluation`
- add `PATCH /logs/{brew_log_id}/evaluation`
- use the specified latest Recommendation endpoint
- return BrewLog lists in `brewed_at DESC, id DESC` order
- add the ExternalBenchmark score trend endpoint and response schema
- enforce required-string trim validation where the MVP contract requires it

For PATCH endpoints:

- omitted field = unchanged
- explicit `null` clears only nullable fields
- empty PATCH = 400
- missing resource = 404
- validate the complete merged resource before saving

## MVP boundaries

Do not add the following before submission readiness is achieved:

- authentication or multi-user support
- AI recommendation
- React / Next.js
- PostgreSQL
- Docker
- deployment work
- Experiment tables or experiment-chain features
- automatic diff or advanced analysis
- other Post-MVP features

Do not perform unrelated architectural refactors unless they are required to satisfy the MVP contract, tests, or reproducibility requirements.

## Verification requirements

Do not call an item complete because the code was written.

Before closing implementation work, verify the relevant behavior with tests or an explicit local acceptance check. Do not invent test results, runtime results, or commit SHAs.

The final submission check must cover a clean setup with no existing SQLite database and verify the main user flow from setup through API/UI usage and tests.

## Repository hygiene

The public repository should contain only information useful for understanding, running, reviewing, or continuing the project.

Do not store personal learning checkpoints or self-assessed weaknesses in this repository. Keep `AGENTS.md` focused on implementation scope, constraints, current priority, and verification rules.

README should describe completed, verified behavior. Do not use README as a backlog or claim unfinished target behavior as implemented.
