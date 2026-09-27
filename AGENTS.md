# coffee-log-web Development Handoff

## Scope

Use this repository (`minamoto2000/coffee-log-web`) as the source of truth for implementation status.

Implementation status must be judged from the repository's actual code, tests, templates, README, and directory structure.

## Current objective

Keep `coffee-log-web` submission-ready for job applications without expanding beyond the Current MVP.

## Verified current state

The repository currently includes:

- aligned MVP API routes and response contracts
- BrewLog + Evaluation transactional creation
- PATCH merge validation
- EquipmentSet snapshot behavior
- Evaluation 1:1 and cascade DB constraints
- deterministic Recommendation with feasibility fallback
- ExternalBenchmark score trend API
- UTC-normalized application datetime handling
- Core Vertical Slice Jinja pages
- submission-critical pytest coverage
- GitHub Actions clean-checkout test and uvicorn smoke verification

Do not treat this list as a substitute for checking the actual implementation and latest CI result.

## Current task

The implementation phase is closed unless a submission-critical failure is found.

Before job-application use:

1. Check the latest GitHub Actions run is green.
2. Read the public README against the actual code.
3. Manually exercise the Core Vertical Slice:
   Equipment Set -> Brew Log + Evaluation -> Recommendation.
4. Fix only reproducibility, correctness, or documentation blockers found by that check.

## MVP boundaries

Do not add the following for submission readiness:

- authentication or multi-user support
- AI recommendation
- React / Next.js
- PostgreSQL
- Docker
- deployment work
- Experiment tables or experiment-chain features
- automatic diff or advanced analysis
- other Post-MVP features

Do not perform unrelated architectural refactors unless required by a verified correctness or reproducibility problem.

## Verification requirements

Do not call an item complete because code exists.

A change is complete only after its relevant tests or explicit acceptance check pass. Never invent runtime results or commit SHAs.

## Repository hygiene

The public repository should contain only information useful for understanding, running, reviewing, or continuing the project.

Do not store personal learning checkpoints or self-assessed weaknesses here.

README must describe completed, verified behavior rather than a target backlog.
