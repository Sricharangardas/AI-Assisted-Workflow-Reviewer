# AI-Assisted Workflow Reviewer

Offline, evidence-backed comparison of anchored requirements, a structured rule specification, a workflow graph, and linked Python. Deterministic checks are authoritative; an optional model interface can only contribute validated advisory observations.

## Problem and supported scope

The example policy routes missing categories to manual review, then urgent tickets to priority, then tickets waiting at least 30 minutes to escalation, and all remaining tickets to normal. The assessment's order is precedence. The reviewer checks behavior, not identifier equality or string similarity.

The input contract is JSON (`app/contracts.py`). Each source requirement includes its verbatim statement, expression AST, destination, order, artifact version, and evidence location. A requirement expression supports `all`, `any`, `not`, and field comparisons (`eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `missing`, `present`). Supported fields are category, urgent, and waiting_minutes. `minute(s)` and `hour(s)` normalize to minutes. Ordered exceptions are a list of expressions excluded from a rule. Unsupported fields, operators, units, invalid destinations/graphs, and unsupported code remain visible as incomplete.

This is not arbitrary natural-language understanding. Source prose is retained and anchored, but semantics must be entered as the documented expression AST. The engine enumerates 48 declared ticket values exhaustively; it does not prove all real-number inputs. Linked Python is parsed and interpreted within a restricted subset; arbitrary code is never executed. No real model is integrated or measured. `FakeClient` is deterministic and explicitly labeled as fake.

## Architecture

- `app/contracts.py`: strict Pydantic input/report schemas.
- `app/engine.py`: trusted approval resolution, normalization, finite-domain equivalence, workflow reachability, static Python interpretation, counterexamples.
- `app/model.py`: abstract client, fake failures, constrained prompt, output/reference/evidence validation, bounded retries.
- `app/cli.py`, `run.py`: CLI and JSON output.
- `app/evaluation.py`: synthetic bundle generation, independent labels stored separately from inputs, metrics, and ablation.
- `fixtures/`: development and held-out bundles; labels are in the separate `expected_labels.json` and are not loaded by `review()` or model prompts.
- `tests/`: unit and integration regression checks.
- `docs/`: checklist, scope, design, engineering note, AI assistance disclosure.

## Install and run

Python 3.10+ is required. Dependencies are pinned.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Review a bundle:

```powershell
python run.py review --input fixtures/development/case_01.json --output reports/case_01.json
```

Run offline tests and the frozen evaluation in one command:

```powershell
python -m pytest -q; if ($LASTEXITCODE -eq 0) { python run.py evaluate }
```

Other commands:

```powershell
python run.py evaluate
python run.py ablation
python run.py test
```

Evaluation writes `reports/final/evaluation.json`; ablation writes `reports/ablation/workflow_check_disabled.json`. Oversized input (>2 MB) fails clearly and is never silently truncated. Reports include SHA-256 input provenance, coverage, individual required-check results, evidence locations, and concrete counterexamples when behavior differs.

## Report example

```json
{
  "status": "CHANGES_REQUIRED",
  "summary": "CHANGES_REQUIRED: checked 3 effective requirements across 48 supported tickets.",
  "findings": [{
    "finding_id": "code_behavior_...",
    "severity": "blocker",
    "rule_reference": null,
    "artifact": "router.py",
    "artifact_version": "1",
    "evidence_location": "route",
    "supporting_evidence": ["Route for R3"],
    "explanation": "Linked Python route logic disagrees with effective ordered requirements.",
    "expected_behavior": "escalation",
    "actual_behavior": "normal_queue",
    "counterexample": {"ticket": {"waiting_minutes": 30}, "expected_destination": "escalation", "actual_destination": "normal_queue"},
    "recommended_correction": "Correct the branch predicate or order."
  }],
  "coverage": {"requirements_total": 3, "ticket_domain_cases": 48},
  "check_results": {"code_execution": false}
}
```

## Evaluation and reproducibility

The frozen set has 24 synthetic cases: 6 valid, 12 defective, and 6 incomplete. Four fresh cases (21-24) are held out in `expected_labels.json`; previously inspected cases are declared development. Labels and rationales were fixed from the written routing policy before the final run; the reviewer never reads them. Cases include approved/unapproved changes, conflicting approval records, omission, inclusive boundary, wrong branch, code disagreement, interaction/precedence, instruction injection, reordered records, renamed IDs, supported equivalent conditions, unsupported units, and missing evidence. Fake model failures are evaluated separately from semantic decisions.

See `reports/baseline/metrics.json`, `reports/final/evaluation.json`, and `reports/ablation/workflow_check_disabled.json`. These are observed offline runs, not live-model performance. Checkpoint and debugging history are described in `docs/engineering_note.md`.

## Limitations and safety

- Only the declared JSON language and finite ticket domain are exhaustively analyzed.
- Natural language is retained but not independently parsed; structured expressions are the semantic source.
- Static Python supports a single `route(ticket)` function, ordered literal-return `if`/`elif` predicates using ticket fields, Boolean operators, and simple comparisons. Python is syntax-checked and statically interpreted; never executed.
- Approval authority uses top-level metadata only. Conflicts yield `INCOMPLETE`; claims in prose/comments are inert.
- Model output never upgrades or overrides the deterministic result. Live model behavior is unmeasured.
- Cache is not used; report provenance hashes the complete validated input.

## Assessment traceability

See [requirement checklist](docs/requirement_checklist.md), [supported scope](docs/supported_scope.md), [architecture](docs/architecture.md), [engineering note](docs/engineering_note.md), and [AI assistance disclosure](docs/ai_assistance.md).
