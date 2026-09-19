# M3 — Task template planning / version 0.2.0

Read input.bundle, previous.evidence and asset_units. Return tasks and exclusions.
Use the professor's domains (quantum, chemistry, biology/life science, materials) and
abilities (perception, inference, design). Synthetic fixtures may use a synthetic domain.
Keep input_scale separate from reasoning_scale; these describe the input object and
geometry needed to solve the task. Do not invent numerical lengths from object labels.
Template names are internal working categories, not a new official 31-class taxonomy.

Each T001-style task cites evidence_ids, explains geometry_necessity, specifies input_plan
and validation_route. xyz_distance and xyz_angle require actual coordinates with confirmed
angstrom units in asset_units. Missing units or assets => eligible=false with explicit
unmet_requirements. evidence_review requires a self-contained reasoning question and
explicit evidence-based answer basis; copying a conclusion is not geometric inference.
Design stays ineligible until a valid design evaluator exists. No forced quota filling.

Pass gate: schema, source linkage, task eligibility and asset availability.
Scientific relevance, two-scale labels and true geometry necessity still need review.

## v0.4 prototype rules (Meeting 4)
Use input.prototype_policy: classify by REASONING scale; input size remains metadata. A large supplied structure with an explicitly localized task can be single-reasoning-scale. Do not infer scale from object labels.
Every task supplies learning_objective (disciplinary geometry concept tested) and selection_rationale (why these entities, not arbitrary rows). A purely arbitrary coordinate subtraction is a software baseline, not a meaningful science prototype. Renaming indices to element names alone is insufficient. Require a supported motif, relationship or scientific interpretation.
Target 10 per domain/scale cell, approximately 3 each ability plus one flexible slot, never a mandatory quota. Design without evaluator stays deferred. Reuse one documented, versioned method per source route and template; do not create bespoke untraceable methods for every row.
