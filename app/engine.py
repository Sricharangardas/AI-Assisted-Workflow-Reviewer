"""Deterministic semantic checks over a finite, documented ticket domain."""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
from typing import Any

from app.contracts import Bundle, Expr, Finding, Requirement, ReviewReport

FIELDS = {"category": (None, "billing", "technical"), "urgent": (False, True), "waiting_minutes": (None, 0, 24, 25, 29, 30, 31, 60)}


def eval_expr(expr: Expr, ticket: dict[str, Any]) -> bool:
    d = expr.model_dump(by_alias=True, exclude_none=True)
    if "all" in d: return all(eval_expr(Expr.model_validate(x), ticket) for x in d["all"])
    if "any" in d: return any(eval_expr(Expr.model_validate(x), ticket) for x in d["any"])
    if "not" in d: return not eval_expr(Expr.model_validate(d["not"]), ticket)
    field, op, value = d.get("field"), d.get("op"), d.get("value")
    actual = ticket.get(field)
    if op == "missing": return actual is None
    if op == "present": return actual is not None
    if actual is None: return op == "eq" and value is None or op == "ne" and value is not None
    if field == "waiting_minutes" and d.get("unit"):
        factor = {"minute": 1, "minutes": 1, "hour": 60, "hours": 60}.get(d["unit"])
        if factor is None: raise ValueError(f"unsupported time unit: {d['unit']}")
        value = value * factor
    return {"eq": lambda: actual == value, "ne": lambda: actual != value, "lt": lambda: actual < value,
            "lte": lambda: actual <= value, "gt": lambda: actual > value, "gte": lambda: actual >= value}[op]()


def route(rules: list[Requirement], ticket: dict[str, Any], fallback: str = "normal_queue") -> str:
    for rule in sorted(rules, key=lambda r: r.order):
        if eval_expr(rule.condition, ticket) and not any(eval_expr(x, ticket) for x in rule.exceptions):
            return rule.destination
    return fallback


def tickets():
    keys = list(FIELDS)
    for vals in itertools.product(*(FIELDS[k] for k in keys)):
        yield dict(zip(keys, vals))


def effective_requirements(bundle: Bundle):
    rules = {r.id: r for r in bundle.requirements}
    by_change: dict[str, set[str]] = {}
    for a in bundle.approvals:
        by_change.setdefault(a.change_id, set()).add(a.decision)
    findings = []
    for c in sorted(bundle.changes, key=lambda x: x.effective_order):
        if c.scope == "revision" and c.revision != bundle.revision:
            if c.revision is None:
                findings.append(("change_scope_ambiguous", c.evidence, c.requirement_id, "Revision-scoped change does not declare a target revision."))
            continue
        decisions = by_change.get(c.id, set())
        if len(decisions) > 1 or (decisions and (("approved" in decisions) != c.approved)):
            findings.append(("approval_conflict", c.evidence, c.requirement_id, "Conflicting top-level approval metadata prevents effective requirement resolution."))
            continue
        # Only top-level change metadata or corroborating records can authorize; prose is never consulted.
        approved = c.approved and (not decisions or decisions == {"approved"})
        if approved and c.replacement:
            if c.requirement_id in rules:
                rules[c.requirement_id] = c.replacement
            else:
                findings.append(("change_target_missing", c.evidence, c.requirement_id, "Approved change targets an unknown requirement."))
    return list(rules.values()), findings


def _finding(fid, sev, ref, art, ver, loc, evidence, msg, expected=None, actual=None, counter=None, correction=""):
    return Finding(finding_id=fid, severity=sev, rule_reference=ref, artifact=art, artifact_version=ver,
        evidence_location=loc, supporting_evidence=evidence, explanation=msg, expected_behavior=expected,
        actual_behavior=actual, counterexample=counter, recommended_correction=correction)


def _py_expr(node: ast.AST) -> Expr:
    """Translate a narrow, side-effect-free ticket predicate AST to the JSON DSL."""
    if isinstance(node, ast.BoolOp):
        key = "all" if isinstance(node.op, ast.And) else "any" if isinstance(node.op, ast.Or) else None
        if not key: raise ValueError("unsupported boolean operator")
        return Expr.model_validate({key:[_py_expr(x).model_dump(by_alias=True,exclude_none=True) for x in node.values]})
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return Expr.model_validate({"not":_py_expr(node.operand).model_dump(by_alias=True,exclude_none=True)})
    if isinstance(node, ast.Compare) and len(node.ops)==1 and len(node.comparators)==1:
        left, right, op = node.left, node.comparators[0], node.ops[0]
        if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and isinstance(left.func.value,ast.Name) and left.func.value.id=="ticket" and left.func.attr=="get" and len(left.args)==1 and isinstance(left.args[0],ast.Constant):
            field=left.args[0].value
        else: raise ValueError("predicate must compare ticket.get('field')")
        val = right.value if isinstance(right,ast.Constant) else None
        ops={ast.Eq:"eq",ast.NotEq:"ne",ast.Lt:"lt",ast.LtE:"lte",ast.Gt:"gt",ast.GtE:"gte",ast.Is:"eq",ast.IsNot:"ne"}
        op_name=ops.get(type(op))
        if op_name is None or not isinstance(right,ast.Constant): raise ValueError("unsupported comparison")
        if val is None and op_name=="eq": op_name="missing"
        if val is None and op_name=="ne": op_name="present"
        return Expr(field=field,op=op_name,value=val)
    if isinstance(node,ast.Name) and node.id in {"True","False"}: return Expr(field="urgent",op="eq",value=node.id=="True")
    raise ValueError("unsupported Python predicate")


def _code_route(source: str, ticket: dict[str, Any]):
    """Inspect a restricted ordered route(ticket) function; never execute code."""
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError("expected one function definition")
    fn = tree.body[0]
    if len(fn.args.args) != 1 or fn.args.args[0].arg != "ticket": raise ValueError("expected route(ticket)")
    def chain(statements):
        for node in statements:
            if isinstance(node,ast.If):
                if len(node.body)!=1 or not isinstance(node.body[0],ast.Return) or not isinstance(node.body[0].value,ast.Constant) or not isinstance(node.body[0].value.value,str):
                    raise ValueError("each route branch must return a literal destination")
                if eval_expr(_py_expr(node.test),ticket): return node.body[0].value.value
                if node.orelse:
                    if len(node.orelse)==1 and isinstance(node.orelse[0],ast.If):
                        tail=chain(node.orelse)
                        if tail!="UNMATCHED": return tail
                    elif len(node.orelse)==1 and isinstance(node.orelse[0],ast.Return):
                        v=node.orelse[0].value
                        if not isinstance(v,ast.Constant) or not isinstance(v.value,str): raise ValueError("fallback must return a literal destination")
                        return v.value
            elif isinstance(node,ast.Return):
                if not isinstance(node.value,ast.Constant) or not isinstance(node.value.value,str): raise ValueError("fallback must return a literal destination")
                return node.value.value
            else: raise ValueError(f"unsupported Python statement: {type(node).__name__}")
        return "UNMATCHED"
    return chain(fn.body)


def review(bundle: Bundle, use_graph=True, use_code=True) -> ReviewReport:
    findings: list[Finding] = []
    effective, approval_issues = effective_requirements(bundle)
    for code, ev, ref, msg in approval_issues:
        findings.append(_finding(code, "incomplete", ref, ev.artifact, ev.version, ev.location, [ev.text], msg, correction="Resolve contradictory approval metadata and rerun review."))
    spec = bundle.specification
    spec_by_ref: dict[str, list] = {}
    for s in spec: spec_by_ref.setdefault(s.requirement_id, []).append(s)
    # Unknown/ambiguous domains stay visible, never become passes.
    incomplete = not use_graph or not use_code or not bundle.code or not bundle.requirements
    if not bundle.code:
        ev=bundle.requirements[0].evidence if bundle.requirements else None
        if ev:
            findings.append(_finding("missing_code_artifact","incomplete",None,"code", "unknown", "code", [ev.text], "No linked Python artifact was provided for the required code check.", correction="Provide a versioned linked Python artifact or explicitly revise the review contract."))
    if not bundle.requirements and bundle.specification:
        findings.append(_finding("missing_source_requirements","incomplete",None,"requirements",bundle.source_version,"requirements",[],"No anchored source requirements were provided.",correction="Provide the written requirements and evidence locations."))
    code_inspected=False
    code_syntax=False
    try:
        for req in effective:
            if req.id not in spec_by_ref:
                findings.append(_finding("missing_spec_"+req.id, "blocker", req.id, "specification", bundle.spec_version, "rules", [req.evidence.text], "Effective source requirement is omitted from the structured specification.", req.destination, "missing", correction="Add a specification rule implementing this requirement."))
        for t in tickets():
            expected = route(effective, t)
            matches = [s for s in spec if eval_expr(s.condition, t)]
            actual = sorted(matches, key=lambda s:s.order)[0].destination if matches else "normal_queue"
            if expected != actual:
                req = next((r for r in effective if route([r], t) == expected), effective[0] if effective else None)
                ref = req.id if req else None
                ev = next((s.evidence for s in matches), (req.evidence if req else bundle.requirements[0].evidence))
                findings.append(_finding("spec_behavior_"+hashlib.sha1(json.dumps(t,sort_keys=True).encode()).hexdigest()[:7], "blocker", ref, ev.artifact, ev.version, ev.location, [ev.text], "Specification routes a supported ticket differently from the effective ordered requirements.", expected, actual, {"ticket":t,"expected_destination":expected,"actual_destination":actual}, "Correct the condition, order, or destination to match the effective requirement."))
                break
        # Compare workflow using deterministic route-condition edges on reachable paths.
        if use_graph:
            nodes = {n.id:n for n in bundle.workflow.nodes}
            outs = {}
            for b in bundle.workflow.branches: outs.setdefault(b.source, []).append(b)
            if bundle.workflow.entry not in nodes: raise ValueError("workflow entry node does not exist")
            for t in tickets():
                exp = route(effective, t)
                cur = bundle.workflow.entry
                seen = set()
                for _ in range(len(nodes)+1):
                    if cur in seen: raise ValueError("workflow contains a reachable cycle")
                    seen.add(cur)
                    n = nodes[cur]
                    if n.kind in ("route", "terminal"): break
                    candidates = [b for b in outs.get(cur, []) if b.condition is None or eval_expr(b.condition,t)]
                    if not candidates: cur="UNMATCHED"; break
                    b = sorted(candidates,key=lambda b:b.order)[0]; cur=b.target
                    if cur not in nodes: raise ValueError("branch targets missing node")
                actual = nodes[cur].id if cur in nodes else cur
                # Route nodes are named by destination in this contract.
                if exp != actual:
                    ev = next((b.evidence for b in bundle.workflow.branches), bundle.requirements[0].evidence)
                    findings.append(_finding("workflow_route_"+hashlib.sha1(json.dumps(t,sort_keys=True).encode()).hexdigest()[:7], "blocker", None, "workflow", bundle.workflow.version, ev.location, [ev.text], "Reachable workflow route disagrees with effective ordered requirements.", exp, actual, {"ticket":t,"expected_destination":exp,"actual_destination":actual}, "Correct the branch condition or destination.")); break
        if use_code:
            for artifact in bundle.code:
                ast.parse(artifact.source)  # syntax validation is separate from behavior inspection
                code_syntax=True
                for t in tickets():
                    expected=route(effective,t); actual=_code_route(artifact.source,t)
                    if expected!=actual:
                        findings.append(_finding("code_behavior_"+hashlib.sha1(json.dumps(t,sort_keys=True).encode()).hexdigest()[:7], "blocker", None, artifact.name, artifact.version, artifact.evidence.location, [artifact.evidence.text], "Linked Python route logic disagrees with effective ordered requirements; code was statically interpreted, not executed.", expected, actual, {"ticket":t,"expected_destination":expected,"actual_destination":actual}, "Correct the branch predicate or order.")); break
                code_inspected=True
    except Exception as exc:
        incomplete=True
        evidence=bundle.code[0].evidence if bundle.code else bundle.requirements[0].evidence
        findings.append(_finding("scope_unreviewed", "incomplete", None, evidence.artifact, evidence.version, evidence.location, [str(exc)], "A required semantic check is outside the declared analyzer capability.", correction="Rewrite the artifact into the documented restricted subset or extend and test the analyzer."))
    blockers=any(f.severity=="blocker" for f in findings)
    status="CHANGES_REQUIRED" if blockers else "INCOMPLETE" if (incomplete or findings) else "PASS"
    return ReviewReport(status=status, summary=f"{status}: checked {len(effective)} effective requirements across {sum(1 for _ in tickets())} supported tickets.", findings=findings,
        coverage={"requirements_total":len(effective),"requirements_in_spec":sum(r.id in spec_by_ref for r in effective),"ticket_domain_cases":sum(1 for _ in tickets()),"verification":"exhaustive over declared finite ticket domain; not arbitrary prose/code","unreviewed_scope":incomplete},
        check_results={"effective_requirements":not bool(approval_issues),"specification_equivalence":not any(f.finding_id.startswith("spec_behavior") or f.finding_id.startswith("missing_spec") for f in findings),"workflow":use_graph,"code_static_inspection":code_inspected,"code_syntax_validation":code_syntax,"code_execution":False},
        provenance={"bundle_id":bundle.bundle_id,"revision":bundle.revision,"input_sha256":hashlib.sha256(bundle.model_dump_json().encode()).hexdigest()})
