# M3 — Task template planning / version 0.4.1

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

## 2026-09-22 geometry dependency contract
Every REAL task, including excluded tasks, supplies geometry_audit (see schema). Synthetic software fixtures may omit it and must never enter the scientific pool.
- geometry_inputs: name the actual geometry information used: coordinates, images, distances, angles, cell parameters or spatial relations. Geometry does NOT mean XYZ only.
- without_geometry: remove that information, including duplicate clues in text; explain which answers remain possible. This is a reasoned counterfactual, NOT a claimed executed model ablation.
- dependent_score_items: name substantive planned scoring items that actually need geometry. No token geometry subquestion attached to otherwise unrelated arithmetic. HOMO/LUMO subtraction with all energies supplied and dipole norms with no spatial relationship fail molecular-geometry necessity, even if an XYZ is attached.
- geometry_dependency: necessary / partial / none / uncertain. partial requires explaining the meaningful geometry-dependent part; none or uncertain => eligible=false, with unmet requirements.
- scale_basis and scale_consistent: identify participating entities, physical span, units, measurement method and convention. A local three-site question uses those sites, not the whole tRNA. Whole-object searches may use the search extent, not the resulting minimum distance. Give compared local structures' ranges separately; do not invent a common frame. Use one stated convention for periodic cell motifs versus shells; do not alternate edge, radius and diameter to fill cells.
- claim_limits and claims_supported: list what can and cannot follow, and what extra evidence stronger claims need. Distances need not determine stability, catalytic access, full-helix regularity, whole-backbone equality or a unique dimer orientation. A computed scalar equality/inequality needs an explicit model and uncertainty scope. A centering selection rule gives necessary allowed-reflection conditions, not a guarantee of nonzero intensity.
- template_family: identify existing same-method questions/source groups. New molecules or domains do not make a new ability. Record basic formula tasks honestly; no need to reject valid lattice-parameter geometry merely because the formula is given.
Perception describes spatial properties. Physical inference must connect geometry to a specified physical consequence; adding a comparison or generic caution does not itself make inference. Source balance and P/I/D targets are batch diagnostics, never pass quotas.
Do not mark scale_consistent or claims_supported true when the evidence is uncertain. Corrected real tasks require a new run with these rules, not edits to accepted snapshots.
