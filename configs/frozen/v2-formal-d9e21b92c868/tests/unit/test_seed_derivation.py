from scripts.run_episode import derive_seeds


def test_environment_and_policy_use_distinct_reproducible_seeds() -> None:
    assert derive_seeds(42) == derive_seeds(42)
    environment_seed, policy_seed = derive_seeds(42)
    assert environment_seed != policy_seed
