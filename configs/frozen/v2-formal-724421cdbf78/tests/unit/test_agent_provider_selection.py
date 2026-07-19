import pytest

from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
from shiftmem.providers.local import DeterministicProvider
from scripts.run_agent_episode import make_provider


def test_deterministic_provider_is_default_offline_choice() -> None:
    assert isinstance(make_provider("deterministic", target_inventory=30), DeterministicProvider)


def test_compatible_provider_loads_environment_without_network(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "secret")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MODEL_NAME", "small-model")
    assert isinstance(make_provider("compatible", target_inventory=30), CompatibleAPIProvider)


@pytest.mark.parametrize("profile", ["bailian", "siliconflow"])
def test_named_provider_forwards_profile_and_model(monkeypatch, profile) -> None:
    captured = {}

    def fake_from_env(
        selected_profile="compatible",
        load_file=True,
        model_override=None,
    ):
        captured.update(
            profile=selected_profile,
            model_override=model_override,
        )
        return ProviderConfig(
            api_key="key",
            base_url="https://example.test/v1",
            model_name="model",
        )

    monkeypatch.setattr(ProviderConfig, "from_env", fake_from_env)

    provider = make_provider(profile, target_inventory=30, model_name="override-model")

    assert isinstance(provider, CompatibleAPIProvider)
    assert captured == {"profile": profile, "model_override": "override-model"}


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        make_provider("unknown", target_inventory=30)
