# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Nightly Eval Runner
# MAGIC
# MAGIC Runs `mlflow.genai.evaluate()` against the 20-turn seed dataset plus a
# MAGIC sample of yesterday's production traces. Alerts (Slack/email) on
# MAGIC scorer p50 regression > 5pp.
# MAGIC
# MAGIC Stub — wires up in Phase 8.

# COMMAND ----------

import argparse
import json
import os
import sys

import mlflow
import pandas as pd

# Make ./eval/scorers.py importable when run as a notebook task.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scorers import policy_citation_present  # noqa: E402


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment_path",
        default="/Shared/steelcase-demo/compass-experiment",
        help="MLflow experiment to log results to.",
    )
    parser.add_argument(
        "--dataset_path",
        default="eval/coop-eval-dataset.jsonl",
        help="JSONL eval dataset path (repo-relative or absolute).",
    )
    parser.add_argument(
        "--endpoint",
        default="compass-supervisor",
        help="Serving endpoint to invoke for each turn.",
    )
    return parser.parse_args()


def load_dataset(path: str) -> pd.DataFrame:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def predict_fn(messages: list[dict], endpoint: str) -> str:
    """Invoke the supervisor agent serving endpoint. TODO Phase 6."""
    # Pseudocode — replace with databricks-sdk ServingEndpointsAPI.query():
    #   client = DatabricksClient()
    #   resp = client.serving_endpoints.query(name=endpoint, messages=messages)
    #   return resp.choices[0].message.content
    raise NotImplementedError("Wire up in Phase 6 once compass-supervisor exists.")


def main():
    args = _parse_args()
    mlflow.set_experiment(args.experiment_path)
    dataset = load_dataset(args.dataset_path)

    with mlflow.start_run(run_name="compass-eval-nightly"):
        mlflow.genai.evaluate(
            data=dataset,
            predict_fn=lambda messages: predict_fn(messages, args.endpoint),
            scorers=[
                mlflow.genai.scorers.Correctness(),
                mlflow.genai.scorers.RetrievalGroundedness(),
                mlflow.genai.scorers.Guidelines(),
                policy_citation_present,
            ],
        )


if __name__ == "__main__":
    main()
