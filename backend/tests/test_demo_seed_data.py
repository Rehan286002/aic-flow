import pytest

from scripts import seed_demo_data


def test_demo_scenarios_have_a_complete_stage_path():
    for scenario in seed_demo_data.SCENARIOS:
        path = seed_demo_data.stage_path_for(scenario)
        assert path[0] == "DRAFT"
        assert path[-1] == scenario["stage"]
        assert len(path) == len(set(path))
        assert set(path).issubset(seed_demo_data.STAGE_RECEIVING_ASSIGNMENT)
        assert scenario["team_key"] in seed_demo_data.DEMO_TEAM_GROUPS


def test_demo_routes_are_explicitly_simulated_not_published_policy():
    for scenario in seed_demo_data.SCENARIOS:
        snapshot = seed_demo_data.make_route_snapshot(scenario)
        assert snapshot["route_status"] == "SIMULATION_ONLY"
        assert snapshot["simulation"] is True
        assert snapshot["regulatory_policy_publication"] == "NOT_PUBLISHED"
        assert "not an AICTE route determination" in snapshot["explanation"]


def test_demo_seed_refuses_ci_and_production_environments(monkeypatch):
    monkeypatch.setattr(seed_demo_data.settings, "app_env", "test")
    with pytest.raises(SystemExit):
        seed_demo_data.require_local_environment()
    monkeypatch.setattr(seed_demo_data.settings, "app_env", "production")
    with pytest.raises(SystemExit):
        seed_demo_data.require_local_environment()


def test_demo_seed_refuses_non_loopback_database(monkeypatch):
    monkeypatch.setattr(seed_demo_data.settings, "app_env", "local")
    monkeypatch.setattr(
        seed_demo_data.settings,
        "database_url",
        "postgresql+psycopg://user:pass@example.invalid/aic_flow",
    )
    with pytest.raises(SystemExit):
        seed_demo_data.require_local_environment()



def test_demo_review_groups_are_synthetic_and_all_scenarios_are_distributed():
    assert set(seed_demo_data.DEMO_TEAM_GROUPS) == {"north", "south", "east"}
    scenario_groups = {scenario["team_key"] for scenario in seed_demo_data.SCENARIOS}
    assert scenario_groups == {"north", "south", "east"}
    for _key, (_name, description) in seed_demo_data.DEMO_TEAM_GROUPS.items():
        assert "not an AICTE regional office" in description
