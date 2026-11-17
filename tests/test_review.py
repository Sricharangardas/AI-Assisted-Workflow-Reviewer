import json
from pathlib import Path
import pytest
from app.contracts import Bundle
from app.engine import review
from app.evaluation import canonical, create_frozen_dataset, DATA
from app.model import FakeClient, request_advisory

def parsed(d): return Bundle.model_validate(d)

def test_canonical_all_routes_pass():
    assert review(parsed(canonical())).status == "PASS"

def test_fallthrough_is_normal_queue_regression():
    report=review(parsed(canonical()))
    assert report.status=="PASS"
    assert report.coverage["ticket_domain_cases"]==48

def test_nested_expression_contract_rejects_ambiguous_shape():
    from pydantic import ValidationError
    from app.contracts import Expr
    Expr.model_validate({"all":[{"field":"urgent","op":"eq","value":True},{"not":{"field":"category","op":"missing"}}]})
    with pytest.raises(ValidationError): Expr.model_validate({"all":[],"field":"urgent","op":"eq","value":True})

def test_missing_linked_code_cannot_pass():
    b=canonical(); b["code"]=[]
    r=review(parsed(b))
    assert r.status=="INCOMPLETE"

def test_boundary_inclusive_30_minutes():
    b=canonical(); b["specification"][2]["condition"]["op"]="gt"
    report=review(parsed(b))
    assert report.status=="CHANGES_REQUIRED"
    assert report.findings[0].counterexample["ticket"]["waiting_minutes"]==30

def test_missing_spec_retains_source_reference():
    b=canonical(); b["specification"].pop(0)
    r=review(parsed(b)); f=next(x for x in r.findings if x.finding_id=="missing_spec_R1")
    assert f.supporting_evidence==["Missing category -> manual review."]

def test_unapproved_change_does_not_apply():
    b=canonical(); base=b["requirements"][2]
    b["changes"]=[{"id":"c1","requirement_id":"R3","effective_order":1,"approved":False,"replacement":{**base,"condition":{"field":"waiting_minutes","op":"gte","value":25}},"evidence":{"artifact":"change","version":"2","location":"c1","text":"unapproved"}}]
    assert review(parsed(b)).status=="PASS"

def test_approved_conflict_is_incomplete():
    b=canonical(); b["changes"]=[{"id":"c1","requirement_id":"R3","effective_order":1,"approved":True,"replacement":b["requirements"][2],"evidence":{"artifact":"change","version":"2","location":"c1","text":"change"}}]
    b["approvals"]=[{"id":"a","change_id":"c1","decision":"approved","actor":"x","timestamp":"t","evidence":{"artifact":"approvals","version":"1","location":"a","text":"approve"}},{"id":"b","change_id":"c1","decision":"rejected","actor":"x","timestamp":"t","evidence":{"artifact":"approvals","version":"1","location":"b","text":"reject"}}]
    assert review(parsed(b)).status=="INCOMPLETE"

def test_python_mismatch_is_static_and_counterexample_backed():
    b=canonical(); b["code"][0]["source"]=b["code"][0]["source"].replace(">= 30","> 30")
    r=review(parsed(b)); f=next(x for x in r.findings if x.finding_id.startswith("code_behavior"))
    assert r.check_results["code_execution"] is False
    assert f.counterexample["ticket"]["waiting_minutes"]==30

def test_model_invalid_reference_is_rejected():
    c=FakeClient("invented_ref")
    r=request_advisory(c,"{}",{"R1"},set())
    assert r["accepted"] is False and c.calls==2

def test_model_valid_fake_has_coverage_and_provenance():
    b=canonical(); c=FakeClient()
    r=request_advisory(c,json.dumps(b),{"R1","R2","R3"},{x["evidence"]["text"] for x in b["requirements"]})
    assert r["accepted"] and r["provenance"]=="fake" and r["request"]["max_tokens"]==1200

def test_model_conflicting_claims_rejected():
    class Conflicting(FakeClient):
        def complete(self,prompt,*,timeout_seconds,max_tokens):
            self.calls+=1
            return json.dumps({"findings":[{"rule_reference":"R1","claim":"A"},{"rule_reference":"R1","claim":"B"}],"coverage":{"complete":True,"reviewed_rule_refs":["R1"]}})
    c=Conflicting(); r=request_advisory(c,"{}",{"R1"},set())
    assert not r["accepted"] and "conflicting claims" in r["error"]

@pytest.mark.parametrize("scenario",["timeout","malformed"])
def test_model_failures_bounded(scenario):
    c=FakeClient(scenario); r=request_advisory(c,"{}",set(),set())
    assert not r["accepted"] and r["calls"]==2

def test_frozen_dataset_counts_and_independent_labels():
    create_frozen_dataset()
    labels=json.loads((DATA/"expected_labels.json").read_text())
    assert len(labels["expected"])>=12 and len(labels["held_out"])>=4

