# M5 — Quality screening / version 0.4.1

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

## 2026-09-22 adversarial geometry review
Supply geometry_audit for every real QA; do NOT copy the M3 verdict without rechecking the final student packet and rubric. Fields are defined by the schema: geometry_inputs, without_geometry, dependent_score_items, geometry_dependency, scale_basis, scale_consistent, claim_limits, claims_supported, template_family. All explanations must be concrete and item-specific.
1. Mentally remove all geometry-bearing information (not just XYZ); identify remaining score. Geometry includes stated distances, cell parameters and spatial relations. Supplied energies plus subtraction do not test molecular geometry. A tiny geometry subpart cannot justify unrelated major scoring claims. necessary/partial requires substantial geometry-dependent scoring; none/uncertain => geometry_required=false.
2. Check actual participating entities against the claimed reasoning range. Local sites cannot inherit whole-object size; global searches can have global search extent. Distinguish cell edge/diagonal, shell radius/diameter and local comparisons. Inconsistent/uncertain scale => scale_consistent=false and single_scale_focus=false.
3. Try alternative geometries or physical explanations consistent with the input. Do not award a unique conclusion when multiple remain possible. Distinguish consistency, necessary conditions, sufficiency and causality. Any unsupported scored claim => claims_supported=false, evidence_support=false, rubric_scorable=false, with explicit issues. Numeric agreement by a second method cannot validate semantics.
4. Solve from the public packet alone: no prior question, hidden full-precision value, missing formula, model metadata or teacher-only table. Align reciprocal ratios, signs, units, indices and precision across question/input/answer/rubric. Accept equivalent tied extrema, and account for rounding of the supplied input.
5. Identify basic/repeated task families and source clusters; avoid counting repeated templates as different capabilities. Check perception/inference labels against the actual scored work. Record missing design evaluator and source imbalance at batch level, without inventing design questions.
6. Any review failure needs a concrete issue and repair location. Do not change pending_human_audit to expert-approved. This is same-session semantic screening; the program checks required records and contradictions, not the truth of scientific prose or executed model ablation.

## Meeting 5: template review versus instance verification
For a stable template, cite the reviewed template/version and inspect instance-specific source, identity, units, selection, numeric verification and departures from its conditions. Do not repeat independent-looking model judgements on every instance or claim that rephrasing a rationale is new validation. Template changes, new source preprocessing and boundary cases require renewed targeted review.
All instances need deterministic I/O checks where feasible; numerical agreement cannot establish the truth of scientific interpretation. Use source/template/risk-stratified semantic sampling after the full numeric pass, with sample IDs and actual results recorded. No fixed sampling fraction has been approved. In this legacy packet, all requested review records remain required; template_engine.py is a separate pilot route and does not bypass catalog admission.


## Four-option single-choice policy
For four-option single-choice tasks, verify all four options under identical conditions, not only the intended key. Unknown alternatives cannot be declared wrong. Reject multiple valid/equivalent structures, overlapping ranges, rounding/tolerance collisions, missing structure representations or leaking evidence. Require reviewer evidence and reasons for all distractors. A design selection task evaluates candidate selection, not open structural generation. Current implementation status is specified_not_implemented; do not certify it merely because label comparison is easy.
