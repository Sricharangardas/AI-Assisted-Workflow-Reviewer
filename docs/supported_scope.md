# Supported scope and grammar

## Source requirement contract

The reviewer preserves the anchored source sentence and evaluates the accompanying JSON predicate. It does not infer logic from unrestricted prose. The accepted expression grammar is:

```text
expr := {"all": [expr, ...]} | {"any": [expr, ...]} | {"not": expr}
      | {"field": field, "op": op, "value"?: scalar, "unit"?: time_unit}
field := category | urgent | waiting_minutes
op := eq | ne | lt | lte | gt | gte | missing | present
time_unit := minute | minutes | hour | hours
```

For time comparisons, values are normalized to minutes. Missing values are represented by JSON null. Evaluation order is ascending integer `order`; earlier matching rules win. Exceptions are evaluated as ordered exclusions. All fallthrough behavior is explicitly `normal_queue` for this scenario.

## Change authority

Only the top-level `Change.approved` field authorizes a change, corroborated by any `ApprovalRecord`. Disagreement or approved/rejected records for one change is a conflict and makes effective requirements incomplete. Prose and code comments are never read for authority. Changes are ordered by `effective_order`; revision-scoped records apply only to the exact bundle revision. Unapproved changes remain suggestions. Multiple approved changes apply in order, with the last replacement taking effect.

## Restricted Python subset

The analyzer accepts one `def route(ticket)` with ordered `if`/`elif` branches whose bodies return a string literal. Predicates use `ticket.get('category'|'urgent'|'waiting_minutes')`, constant comparison, `and`, `or`, `not`, and `is None`/`is not None`. A final literal string return is the fallback. Imports, assignments, loops, calls other than the field getter, dynamic values, and arbitrary statements are unsupported. `ast.parse` validates syntax; the analyzer translates approved AST shapes into its expression interpreter. It never calls `exec`, `eval`, imports the artifact, or executes arbitrary Python.

## Workflow and verification domain

The entry node must exist. Decision branches are tested in ascending `order`; the first true branch is followed. Route node IDs are destinations. Reachable cycles, absent targets, or missing routes block proof and produce `INCOMPLETE`. The finite domain contains `category ∈ {null,billing,technical}`, `urgent ∈ {false,true}`, and `waiting_minutes ∈ {null,0,24,25,29,30,31,60}`: 48 combinations. Verification is exhaustive only within these enumerated values, not continuous waiting times or arbitrary ticket fields.
