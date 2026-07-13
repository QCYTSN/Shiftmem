import json

from shiftmem.providers.base import ProviderResponse
from scripts.qualify_models import execute_qualification


class RuleProvider:
    def generate(self, request):
        observation = request.observation
        demand = observation["recent_history"][-1]["demand"]
        quantity = demand
        if observation["pipeline_inventory"]:
            quantity = 0
        if observation["costs"]["stockout"] >= 20:
            quantity += 10
        memory_ids = [
            item["memory_id"]
            for item in request.memory
            if item.get("status") == "active"
        ]
        content = json.dumps(
            {
                "order_quantity": quantity,
                "supplier_id": "standard",
                "used_memory_ids": memory_ids,
                "confidence": 0.8,
                "reason": "rule provider",
            }
        )
        return ProviderResponse(
            text=content,
            input_tokens=10,
            output_tokens=5,
            latency_ms=1,
        )


def test_execute_qualification_writes_safe_raw_and_aggregate_outputs(tmp_path) -> None:
    config = {
        "repetitions": 2,
        "models": [
            {
                "label": "open-qwen",
                "profile": "siliconflow",
                "model_id": "Qwen/Qwen3.5-35B-A3B",
                "role": "formal_candidate",
            }
        ],
    }
    raw = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"

    summaries = execute_qualification(
        config,
        raw,
        summary,
        provider_factory=lambda profile, model_id: RuleProvider(),
    )

    assert summaries[0]["qualifies"] is True
    assert summaries[0]["profile"] == "siliconflow"
    assert summaries[0]["model_id"] == "Qwen/Qwen3.5-35B-A3B"
    assert len(raw.read_text(encoding="utf-8").splitlines()) == 16
    combined = raw.read_text(encoding="utf-8") + summary.read_text(encoding="utf-8")
    assert "API_KEY" not in combined
    assert "api_key" not in combined
