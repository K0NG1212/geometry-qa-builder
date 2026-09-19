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

## v0.4 student, teacher, reviewer checks
Set disciplinary_meaning=true only if the selected relation tests a stated disciplinary geometry concept and entity selection is justified. Arbitrary atom-pair arithmetic fails even if numerically correct. This judgement remains same-session screening, not expert certification.
entity_identity_clear: entities, supported identity/motif, indices and XYZ row convention agree with actual assets. attachments_complete: all referenced materials exist locally in the supplied bundle and suffice to solve; a URL alone is not an attachment. single_scale_focus: reasoning is localized to one declared physical range; a larger input file alone is not cross-scale reasoning.
Student: can I solve this using the supplied question/instructions/attachments? Teacher: what geometry concept is tested, why these entities? Reviewer: what unsupported assumption, leakage, wrong quote, missing condition or untested scoring rule could invalidate it? Record concrete evidence in notes; uncertainty => false and an issue. Every failed check is a revision reason.
