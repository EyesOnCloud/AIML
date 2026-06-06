import kfp
from kfp import dsl
from kfp.dsl import component, Output, Artifact, Input
import requests

# ── COMPONENT 1: Test v4 Baseline ────────────────────────────────────────────
@component(
    base_image="eyesoncloud/pipeline-runtime:latest",
)
def test_v4_baseline(
    v4_service_url: str,
    output_metrics: Output[Artifact]
):
    """
    Sends 10 test messages to v4 agent.
    v4 has no confidence field — records 0 for all.
    Saves baseline metrics JSON as pipeline artifact.
    """
    import requests, json

    test_messages = [
        "check my balance",
        "my card is lost",
        "i want a loan",
        "unauthorized transaction",
        "hello",
        "what is my account balance",
        "fraud on my account",
        "need help with PIN",
        "how do I apply for a loan",
        "good morning"
    ]

    results = []
    for msg in test_messages:
        try:
            resp = requests.get(
                f"{v4_service_url}/chat",
                params={"message": msg},
                timeout=5
            ).json()
            results.append({
                "message": msg,
                "intent": resp.get("intent"),
                "confidence": resp.get("confidence", 0.0),  # v4 returns None
                "bot": resp.get("bot")
            })
        except Exception as e:
            results.append({"message": msg, "error": str(e)})

    confidences = [r.get("confidence", 0.0) for r in results if "error" not in r]
    metrics = {
        "version": "v4",
        "total_tested": len(results),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "results": results
    }

    with open(output_metrics.path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"V4 baseline: avg_confidence={metrics['avg_confidence']:.3f}")

# ── COMPONENT 2: Test v6 New Feature ─────────────────────────────────────────
@component(
    base_image="eyesoncloud/pipeline-runtime:latest",
)
def test_v6_features(
    v6_service_url: str,
    output_metrics: Output[Artifact]
):
    """
    Sends same 10 messages to v6 agent.
    v6 returns confidence scores — measures the new feature.
    """
    import requests, json

    test_messages = [
        "check my balance",
        "my card is lost",
        "i want a loan",
        "unauthorized transaction",
        "hello",
        "what is my account balance",
        "fraud on my account",
        "need help with PIN",
        "how do I apply for a loan",
        "good morning"
    ]

    results = []
    for msg in test_messages:
        try:
            resp = requests.get(
                f"{v6_service_url}/chat",
                params={"message": msg},
                timeout=5
            ).json()
            results.append({
                "message": msg,
                "intent": resp.get("intent"),
                "confidence": resp.get("confidence", 0.0),
                "low_confidence_flag": resp.get("low_confidence_flag", False),
                "bot": resp.get("bot")
            })
        except Exception as e:
            results.append({"message": msg, "error": str(e)})

    confidences = [r.get("confidence", 0.0) for r in results if "error" not in r]
    low_conf_count = sum(1 for r in results if r.get("low_confidence_flag"))

    metrics = {
        "version": "v6",
        "total_tested": len(results),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "low_confidence_rate": low_conf_count / len(results) if results else 1.0,
        "results": results
    }

    # Also fetch /metrics endpoint from v6
    try:
        v6_metrics = requests.get(f"{v6_service_url}/metrics", timeout=3).json()
        metrics["v6_internal_metrics"] = v6_metrics
    except:
        pass

    with open(output_metrics.path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"V6 feature test: avg_confidence={metrics['avg_confidence']:.3f}, "
          f"low_conf_rate={metrics['low_confidence_rate']:.3f}")

# ── COMPONENT 3: Evaluate — Pass/Fail Decision ────────────────────────────────
@component(
    base_image="eyesoncloud/pipeline-runtime:latest"
)
def evaluate_and_decide(
    v4_metrics: Input[Artifact],
    v6_metrics: Input[Artifact],
    promote_threshold_confidence: float,
    promote_threshold_low_conf_rate: float,
    decision: Output[Artifact]
):
    """
    Compares v4 and v6 metrics.
    Promotes v6 if:
      - avg_confidence > promote_threshold_confidence
      - low_confidence_rate < promote_threshold_low_conf_rate
    Otherwise triggers rollback.
    """
    import json

    with open(v4_metrics.path) as f:
        v4 = json.load(f)
    with open(v6_metrics.path) as f:
        v6 = json.load(f)

    v6_avg_conf = v6.get("avg_confidence", 0.0)
    v6_low_conf_rate = v6.get("low_confidence_rate", 1.0)

    passed = (
        v6_avg_conf > promote_threshold_confidence and
        v6_low_conf_rate < promote_threshold_low_conf_rate
    )

    result = {
        "v4_avg_confidence": v4.get("avg_confidence", 0.0),
        "v6_avg_confidence": v6_avg_conf,
        "v6_low_confidence_rate": v6_low_conf_rate,
        "thresholds": {
            "min_avg_confidence": promote_threshold_confidence,
            "max_low_conf_rate": promote_threshold_low_conf_rate
        },
        "decision": "PROMOTE" if passed else "ROLLBACK",
        "reason": (
            f"V6 avg_confidence={v6_avg_conf:.3f} "
            f"({'PASS' if v6_avg_conf > promote_threshold_confidence else 'FAIL'}) | "
            f"low_conf_rate={v6_low_conf_rate:.3f} "
            f"({'PASS' if v6_low_conf_rate < promote_threshold_low_conf_rate else 'FAIL'})"
        )
    }

    with open(decision.path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*50}")
    print(f"DECISION: {result['decision']}")
    print(f"REASON:   {result['reason']}")
    print(f"{'='*50}\n")

# ── COMPONENT 4: Scale v6 (Promote) ──────────────────────────────────────────
@component(
    base_image="bitnami/kubectl:latest"
)
def promote_v6(decision: Input[Artifact]):
    """
    Reads decision artifact.
    If PROMOTE: scales v6 to 2 replicas.
    Demonstrates pipeline-driven deployment action.
    """
    import json, subprocess

    with open(decision.path) as f:
        d = json.load(f)

    if d.get("decision") == "PROMOTE":
        print("Promoting v6: scaling to 2 replicas...")
        result = subprocess.run([
            "kubectl", "scale", "deployment", "banking-agent-v6",
            "-n", "banking-app",
            "--replicas=2"
        ], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Warning: {result.stderr}")
    else:
        print(f"Skipping promote — decision was: {d.get('decision')}")

# ── PIPELINE DEFINITION ───────────────────────────────────────────────────────
@dsl.pipeline(
    name="banking-agent-feature-validation",
    description="Validates confidence scoring feature (v4→v6) and promotes if thresholds met"
)
def banking_agent_pipeline(
    v4_service_url: str = "http://banking-agent-v4.banking-app.svc.cluster.local:8080",
    v6_service_url: str = "http://banking-agent-v6.banking-app.svc.cluster.local:8081",
    promote_threshold_confidence: float = 0.5,
    promote_threshold_low_conf_rate: float = 0.3
):
    # Step 1: Test v4
    v4_task = test_v4_baseline(
        v4_service_url=v4_service_url
    )

    # Step 2: Test v6 (runs in parallel with v4 — KFP detects no dependency)
    v6_task = test_v6_features(
        v6_service_url=v6_service_url
    )

    # Step 3: Evaluate (depends on both v4 and v6 results)
    eval_task = evaluate_and_decide(
        v4_metrics=v4_task.outputs["output_metrics"],
        v6_metrics=v6_task.outputs["output_metrics"],
        promote_threshold_confidence=promote_threshold_confidence,
        promote_threshold_low_conf_rate=promote_threshold_low_conf_rate
    )

    # Step 4: Promote (depends on decision)
    promote_task = promote_v6(
        decision=eval_task.outputs["decision"]
    )

# ── COMPILE PIPELINE ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from kfp import compiler
    compiler.Compiler().compile(
        pipeline_func=banking_agent_pipeline,
        package_path="banking_agent_pipeline.yaml"
    )
    print("Pipeline compiled: banking_agent_pipeline.yaml")
