# Assessment requirement checklist

Mapped against all three pages of `ShodhAI_MLAssessment.pdf` (R1-R3, Stages 1-4, dataset/verification, and submission).

| Assessment requirement | Implementation | Evidence / test |
|---|---|---|
| Canonical missing-category, urgent, >=30-minute and default routes | `app/evaluation.py`, `app/engine.py` | `test_canonical_all_routes_pass`, fallthrough regression |
| Anchored requirements, versions, locations, mappings, omission references | `app/contracts.py`, `app/engine.py` | Pydantic contracts; `test_missing_spec_retains_source_reference` |
| Numeric operators, missing values, AND/OR/NOT, time units, exceptions, order | `Expr`, `Requirement`, engine | boundary, unsupported-unit review; finite-domain analysis |
| Approved changes, scope/order, prose claims untrusted, conflicts visible | `Change`, `ApprovalRecord`, `effective_requirements` | approval tests; prose is never consulted for authority |
| Spec, reachable workflow and linked code comparisons with counterexamples | `app/engine.py` | workflow/code regressions; `run.py evaluate` |
| Equivalence, reordered serialized rules, renamed IDs, supported paraphrase | semantic conditions and cases 02/03 | frozen evaluation labels |
| Model abstraction, fake, prompt, validation and bounded failures | `app/model.py` | malformed, timeout, invented-reference tests |
| JSON status, evidence, coverage, check results; no arbitrary execution | `ReviewReport`, CLI | pytest suite; code execution explicitly false |
| 12+ cases, 3 valid, 6 defective, 3 incomplete; 4 held out | frozen fixtures and separate labels | `app/evaluation.py`, `fixtures/expected_labels.json` |
| Baseline/final, metrics, debugging evidence, ablation | `reports/`, `docs/engineering_note.md` | generated actual-run results |
| CPU offline install, CLI, pinned dependencies | `requirements.txt`, `run.py` | README single command |
| Limitations, source grammar, restricted Python subset, AI disclosure | `docs/`, README | documented scope |

Known constrained scope: user prose is anchored and retained verbatim but semantic interpretation is supplied as a validated expression AST; the program does not infer arbitrary natural-language policies. It exhaustively analyzes a finite ticket domain (48 values) and supported predicates, not every possible real-valued input. Arbitrary Python is never run.
