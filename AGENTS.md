# coffee-log-web Development Handoff

## Scope

For implementation continuation chats, use only this repository (`minamoto2000/coffee-log-web`) as the GitHub reference source.

Do not depend on `career-management-private` or other repositories in the continuation chat. If something cannot be confirmed from this repository or from the current conversation, state that it is unconfirmed instead of guessing.

Implementation status must be judged from this repository's actual code, README, tests, templates, and directory structure.

## Current implementation state

Confirmed in this repository:

- EquipmentSet CRUD foundation is implemented.
- BrewLog + Evaluation creation is implemented.
- BrewLog list/detail/delete is implemented.
- Evaluation is deleted by DB cascade when its BrewLog is deleted.
- BrewLog PATCH is implemented with merged-resource validation.
- BrewLog validation includes numeric bounds, trimmed `bean_label`, pours ordering, pours total vs. `water_g`, and brewing-time ordering.
- ExternalBenchmark create/list/detail/delete and basic benchmark pages are present.

Recent BrewLog PATCH commits:

- `ded6b763f4792ec8d0e7c1fadc6cdad98d82abe5` — `models.py` validation and `BrewLogUpdateRequest`
- `bee69e32ba30c0005e1f1eb8cc0f5ca032baf240` — `PATCH /logs/{brew_log_id}`

## Current next work

Resume with Evaluation retrieval and partial update:

- `GET /logs/{brew_log_id}/evaluation`
- `PATCH /logs/{brew_log_id}/evaluation`

Do not add a separate Evaluation POST; Evaluation is created together with BrewLog in the current implementation.

For Evaluation PATCH, preserve the same partial-update semantics used for BrewLog PATCH:

- omitted field = unchanged
- explicit `null` is allowed only for nullable fields
- empty PATCH = 400
- missing Evaluation = 404
- merge the existing Evaluation with the patch, then validate the complete merged result

## Learning / review mode

The user is implementing the code and wants implementation supervision plus understanding checks.

When showing code, explain what each line or component means in beginner-friendly terms: what it does, why it exists, and the key Python/FastAPI/Pydantic concept involved.

Prefer short open-ended checks one question at a time. If the user says they do not understand, explain the concept before asking the next question.

Current understanding checkpoint:

- Understands that `model_dump(exclude_unset=True)` distinguishes omitted fields from explicitly supplied `null`.
- Understands that `merged_data.update(update_data)` overlays PATCH values on existing values.
- Understands that merged validation checks the complete post-update resource, not only the fields sent in PATCH.
- Understands that `pours` total is calculated for validation; `water_g` is not automatically rewritten from the pours total.
- Needs more practice explaining Python exception handling, especially `except ValidationError as exc` and converting it to `HTTPException(status_code=422, ...)`.

## Response style

- Be concise and strict about implementation correctness.
- Do not claim implementation is complete without checking this repository.
- Do not invent commit SHAs or test results.
- Keep the implementation sequence narrow; avoid unrelated refactors or post-MVP expansion.
