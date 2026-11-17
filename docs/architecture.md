# Architecture

`Bundle` is a strict Pydantic contract. Requirements, specs, workflow nodes/edges, snippets, changes, approvals, versions, and evidence locations are data rather than executable instructions. The report carries status, findings, coverage, check outcomes, and an input digest.

The deterministic engine first derives effective requirements from authorized changes. It then enumerates the declared ticket domain and compares first-match routing behavior across requirements, specification, graph paths, and the supported Python AST subset. First differing tickets become counterexamples with expected and actual destinations. This makes precedence and boundary interactions visible. Missing mapped rules cite the source requirement directly.

There is no similarity score and IDs are informational. Rule matching uses semantics and explicit order, so renamed IDs and reserialized rule lists can remain equivalent. The finite-domain limits are explicit in reports and docs. A required check disabled by ablation yields `INCOMPLETE`, preventing false PASS.

The model interface is isolated. The fake client covers timeout, malformed JSON, and invented references. Responses are Pydantic validated and evidence/reference checked under bounded retries. Model suggestions cannot authorize changes or affect deterministic status. No paid endpoint or key is configured.
