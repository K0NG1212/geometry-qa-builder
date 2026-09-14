# M5 — Quality screening / version 0.2.0

Review each item in previous.qa against original bundle, evidence, tasks and units.
Return one review per qa_id with all checks and explicit issues. Do not trust the
generator's self-assessment. False for uncertainty. Sequential review in one Codex
session is NOT independent review, blind review or expert certification.

Check sufficient_input, evidence_support, geometry_required, no_answer_leakage,
conditions_preserved and rubric_scorable. In particular compare atom indices/angle
vertex and units in question, verifier, reference_answer and rubric. Check whether
the input alone permits solving the task and whether it leaks the requested conclusion.
Coordinate calculations cannot verify stability, causality or quantum properties.
Textual inference needs evidence of the claimed relationship with preserved conditions.
Record source pointers in notes where useful. Do not grant benchmark-ready status.

Pass gate: full review coverage and schema. Export aggregates failed flags and numbers;
all survivors remain pending human audit. Empty QA yields empty reviews, not success.
