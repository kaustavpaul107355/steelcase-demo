# COMPASS Eval Dataset

Format compatible with `mlflow.genai.evaluate()`. One JSON object per line.

## Schema

```jsonc
{
  "inputs":  { "messages": [{ "role": "user", "content": "<question>" }] },
  "expectations": {
    "expected_tool":     "genie | ka | create_nudge_campaign | advance_claim | save_view | refuse",
    "expected_facts":    ["<substring that MUST appear in the answer>", ...],
    "expected_metrics":  ["<metric_view names referenced>", ...],
    "must_cite_corpus":  true | false,
    "guidelines":        ["<short rule for the Guidelines scorer>", ...]
  },
  "tags": {
    "act":      "1..11",
    "category": "forfeiture | policy | action | roi | governance | adversarial",
    "persona":  "maya | eliot | priya"
  }
}
```

## Scorers (configured in the evaluation harness)

- **Correctness** (built-in) — answer contains the expected facts.
- **RetrievalGroundedness** (built-in) — answer is supported by retrieved corpus chunks (KA-routed turns only).
- **Guidelines** (built-in) — each rule in `expectations.guidelines` is satisfied.
- **`policy_citation_present`** (custom `@scorer`) — for any turn with `expected_tool == "ka"` or `must_cite_corpus == true`, the answer must include at least one `KA-*` doc_id citation.

## Running

```python
import mlflow
import pandas as pd

dataset = pd.read_json("eval/coop-eval-dataset.jsonl", lines=True)

mlflow.genai.evaluate(
    data=dataset,
    predict_fn=lambda messages: agent.invoke({"messages": messages}),
    scorers=[
        mlflow.genai.scorers.Correctness(),
        mlflow.genai.scorers.RetrievalGroundedness(),
        mlflow.genai.scorers.Guidelines(),
        policy_citation_present,    # custom @scorer, defined in eval/scorers.py
    ],
)
```

A nightly Databricks Job runs this against a sample of production traces and alerts on >5pp drop in any scorer's p50.
