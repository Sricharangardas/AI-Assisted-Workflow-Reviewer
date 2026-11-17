"""Validated bundle contracts for the supported review language."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    artifact: str
    version: str
    location: str
    text: str


class Expr(StrictModel):
    """JSON expression AST: all/any/not or field/op/value/unit."""
    all: list[Expr] | None = None
    any: list[Expr] | None = None
    not_: Expr | None = Field(default=None, alias="not")
    field: str | None = None
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "missing", "present"] | None = None
    value: Any = None
    unit: str | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        logical=sum(x is not None for x in (self.all,self.any,self.not_))
        comparison=self.field is not None or self.op is not None
        if logical + int(comparison) != 1:
            raise ValueError("expression must contain exactly one logical operator or field comparison")
        if comparison and (self.field is None or self.op is None):
            raise ValueError("field comparisons require both field and op")
        if comparison and self.op not in ("missing","present") and self.value is None and self.op not in ("eq","ne"):
            raise ValueError("ordered comparisons require a non-null value")
        if self.all is not None and not self.all or self.any is not None and not self.any:
            raise ValueError("all/any expressions must contain at least one condition")
        return self


class Requirement(StrictModel):
    id: str
    statement: str
    condition: Expr
    destination: str
    order: int
    evidence: Evidence
    exceptions: list[Expr] = Field(default_factory=list)
    references: dict[str, str] = Field(default_factory=dict)


class Change(StrictModel):
    id: str
    requirement_id: str
    scope: Literal["requirement", "revision"] = "requirement"
    revision: str | None = None
    effective_order: int
    approved: bool
    approved_by: str | None = None
    approved_at: str | None = None
    replacement: Requirement | None = None
    evidence: Evidence


class SpecRule(StrictModel):
    id: str
    requirement_id: str
    condition: Expr
    destination: str
    order: int
    evidence: Evidence


class WorkflowNode(StrictModel):
    id: str
    kind: Literal["decision", "route", "terminal"]
    evidence: Evidence


class WorkflowBranch(StrictModel):
    id: str
    source: str
    target: str
    condition: Expr | None = None
    requirement_id: str | None = None
    order: int = 0
    evidence: Evidence


class Workflow(StrictModel):
    version: str
    entry: str
    nodes: list[WorkflowNode]
    branches: list[WorkflowBranch]


class CodeArtifact(StrictModel):
    name: str
    version: str
    language: Literal["python"] = "python"
    source: str
    evidence: Evidence


class ApprovalRecord(StrictModel):
    id: str
    change_id: str
    decision: Literal["approved", "rejected"]
    actor: str
    timestamp: str
    evidence: Evidence


class Bundle(StrictModel):
    bundle_id: str
    revision: str
    source_version: str
    requirements: list[Requirement]
    changes: list[Change] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    spec_version: str
    specification: list[SpecRule]
    workflow: Workflow
    code: list[CodeArtifact] = Field(default_factory=list)
    model_scenario: str | None = None


class Finding(StrictModel):
    finding_id: str
    severity: Literal["blocker", "warning", "incomplete"]
    rule_reference: str | None = None
    artifact: str
    artifact_version: str
    evidence_location: str
    supporting_evidence: list[str]
    explanation: str
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    counterexample: dict[str, Any] | None = None
    recommended_correction: str


class ReviewReport(StrictModel):
    status: Literal["PASS", "CHANGES_REQUIRED", "INCOMPLETE"]
    summary: str
    findings: list[Finding]
    coverage: dict[str, Any]
    check_results: dict[str, Any]
    provenance: dict[str, Any] = Field(default_factory=dict)


Expr.model_rebuild()
