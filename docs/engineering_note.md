# Engineering note

## Supported scope and decisions

This reviewer accepts strict JSON contracts for anchored requirements, structured rules, workflow branches, Python snippets, and top-level approval metadata. Policy meaning is represented in a restricted expression AST rather than guessed from prose. The engine exhaustively enumerates a finite 48-ticket domain and applies first-match order, exceptions, missing-value checks, and minute/hour normalization. It parses and interprets only the documented pure Python route subset; it never executes submitted code. Reports distinguish static inspection, syntax validity, and code execution. Any missing required artifact, ambiguous approval, unsupported unit, or unsupported syntax prevents PASS.

The graph implementation is custom and small. The optional model client is separated from deterministic verification. Model suggestions are untrusted, evidence-checked, reference-checked, coverage-checked and bounded to two calls. No live API was available or used; fake-client metrics are reported separately.

## Semantic verification

The effective policy is formed from approved changes in declared order. Top-level change authority is corroborated against approval records; conflicts abstain. Requirement/spec/workflow/code behavior is evaluated on the same 48 inputs. A mismatch records a concrete ticket and expected/actual destinations. Serialized order is distinct from semantic `order`, and rule IDs do not determine behavior. Exhaustiveness applies only to the declared finite domain, not continuous real values or unrestricted natural language.

## Evaluation

The frozen set contains 16 cases (4 valid, 8 defective, 4 incomplete), with development cases 01-12 and held-out cases 13-16. Expected labels and rationales are stored separately in `fixtures/expected_labels.json`; they are manually derived from the policy and are never loaded by the reviewer. The baseline and final reports use the same `frozen-v2` set and configuration. On the recorded run, decision correctness is 16/16; false passes are 0/8 defective cases; false blocks are 0/4 valid cases; incomplete outcomes are 0/4 valid, 0/8 defective, and 4/4 incomplete cases. Runtime, fake model calls, and retries are in the machine-readable report. Unsupported finding quality and evidence location precision were not independently adjudicated, so no accuracy claim is made for those measures. Live-model performance was not measured.

## Debugging examples

1. **Recursive Pydantic expression declaration.** Actual failing output on startup: `TypeError: unsupported operand type(s) for |: 'str' and 'NoneType'` while evaluating the `"Expr" | None` annotation. The annotation had been quoted inside a module already using postponed annotations, so Pydantic received a string operand in a union. Changed recursive fields to `Expr | None` and `list[Expr] | None`; `test_nested_expression_contract_rejects_ambiguous_shape` and the full suite verified model construction and nested AST validation.

2. **Fallthrough destination mismatch.** The first actual evaluation run blocked a canonical bundle. Its report showed the ticket `{category: billing, urgent: false, waiting_minutes: null}` with engine expected `UNMATCHED` and workflow actual `normal_queue`. The engine had represented the final policy as no matching rule, although the written requirement explicitly routes all remaining tickets to normal. Corrected the rule interpreter's terminal behavior to `normal_queue`; `test_fallthrough_is_normal_queue_regression` verifies all 48 inputs no longer produce a fallthrough disagreement. This was a real implementation failure, not injected fault.

## Ablation

The controlled ablation disables workflow graph checking and leaves all other bundle inputs and settings fixed. Workflow-only case 06 changes from `CHANGES_REQUIRED` to `INCOMPLETE`; the system abstains because a required check was not run. Valid cases also move from PASS to INCOMPLETE. This shows the graph check contributes blocker evidence while the report status guard prevents the ablated system from claiming a pass. See `reports/ablation/workflow_check_disabled.json`.

## Limitations

There is no unrestricted prose parser, full Python interpreter, real-valued theorem prover, or live model. The reviewer can miss defects outside declared ticket values and the supported ASTs; such scope is stated in every report. The current synthetic evaluation is small and is not evidence of production performance. Model output adds possible ambiguity suggestions only; deterministic checks remain the source of correctness.
