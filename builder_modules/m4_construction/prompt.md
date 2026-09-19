# M4 — Construction plan / version 0.2.0

Return a construction PLAN according to output_schema, only for eligible tasks in
previous.tasks. At most input.max_questions items, zero is allowed. Do NOT supply
answer_numeric or reference_answer: trusted code creates those fields after import.

For numeric tasks: answer_text=null; provide exact existing asset IDs, verifier kind,
one-based atom_indices (angle vertex is the middle index), tolerance, and units
(distance: angstrom; angle: degree). Tolerance must be <=0.001 angstrom / <=0.1 degree.
Question wording MUST name the same atoms, vertex and quantity as the verifier.
Rubric must match the quantity and tolerance. Do not embed a guessed numeric answer
in the question, model_input, rubric or limitations. No generated code is executed.

For evidence_review: verifier=null, units='', answer_text is a concise supported
reference answer preserving all conditions. This remains an unverified textual candidate.
Every item includes source quotations in answer_refs, linked evidence_ids, limitations,
standalone question and model_input. Internal evidence and answers are not model input.
Do not copy target conclusions into the model input. Coordinates come from bundle assets,
not model imagination. Use Q001-style IDs and preserve task_id/ability.

Pass gate: schema, task linkage, unit evidence, valid indices and deterministic computation.
Question/indices agreement and scientific significance require the review module.

## v0.4 complete exam-style question
Name the chemical/disciplinary entities and relevant relation before giving row indices. Index labels locate entities; they do not replace identities or the learning objective. XYZ atom row is one-based after two header lines; distinguish file line vs atom row. Use provided identity/connectivity evidence, never infer a bond or functional group solely from proximity.
Provide a standalone question plus complete instructions and actual local input assets. Preserve quantity, units, central atom, conformer, rounding and rubric. Request a single-scale reasoning task; explicitly localize the relevant region of larger attachments. M6 assembles question, instructions and sanitized assets into a complete student input and a separate answer key.
