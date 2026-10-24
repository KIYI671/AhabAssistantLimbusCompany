"""Migration preserves explicit choices, team independence and unrelated values."""

import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "optional_migration_test", Path(__file__).resolve().parents[1] / "module/config/optional_migration.py"
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_legacy_team_switches_migrate_without_mutating_teams():
    data = {"teams": {"1": {"rabbit_lower_chain": True}, "2": {"rabbit_animation_hold": True}}}
    teams = copy.deepcopy(data["teams"])
    migration.migrate_global_battle_options(data)
    assert data["mirror_lower_chain"] and data["battle_speed_hold"]
    assert data["teams"] == teams


def test_explicit_new_false_wins_over_legacy_true():
    data = {"mirror_lower_chain": False, "battle_speed_hold": False,
            "ego_animation_hold": True, "combat_speed_hold": True,
            "teams": {"1": {"rabbit_lower_chain": True, "rabbit_animation_hold": True}}}
    migration.migrate_global_battle_options(data)
    assert data["mirror_lower_chain"] is False and data["battle_speed_hold"] is False
    assert "ego_animation_hold" not in data and "combat_speed_hold" not in data


def test_old_speed_switches_merge_by_or_and_global_false_overrides_old_team():
    for animation, combat in ((False, False), (True, False), (False, True), (True, True)):
        data = {"ego_animation_hold": animation, "combat_speed_hold": combat,
                "teams": {"1": {"rabbit_animation_hold": True}}}
        migration.migrate_global_battle_options(data)
        assert data["battle_speed_hold"] is (animation or combat)


def test_floor_exit_copies_to_each_team_preserving_explicit_new_choice_and_weights():
    data = {"floor_3_exit": True, "teams": {
        "1": {"rabbit_ego_name": "完整名称", "rabbit_observe_rules": [[3, 2, 5]]},
        "2": {"floor_3_exit": False, "route_node_weights": {"event": 99}},
    }}
    before = copy.deepcopy(data)
    migration.migrate_global_battle_options(data)
    assert "floor_3_exit" not in data
    assert data["teams"]["1"] == {**before["teams"]["1"], "mirror_floor_limit": 3}
    assert data["teams"]["2"] == {"mirror_floor_limit": 5, "route_node_weights": {"event": 99}}
    data["teams"]["1"]["mirror_floor_limit"] = 1
    assert data["teams"]["2"]["mirror_floor_limit"] == 5


def test_legacy_global_floor_exit_applies_to_default_teams_when_missing():
    defaults = {"1": {"team_number": 1}, "2": {"team_number": 2}}
    data = migration.migrate_global_battle_options({"floor_3_exit": True}, defaults)
    assert all(team["mirror_floor_limit"] == 3 for team in data["teams"].values())
    assert defaults == {"1": {"team_number": 1}, "2": {"team_number": 2}}


def test_migration_is_idempotent_and_new_choices_remain_authoritative():
    data = {"floor_3_exit": True, "teams": {"1": {"rabbit_lower_chain": True}}}
    migration.migrate_global_battle_options(data)
    data["mirror_lower_chain"] = False
    data["battle_speed_hold"] = False
    data["teams"]["1"]["mirror_floor_limit"] = 5
    before = copy.deepcopy(data)
    migration.migrate_global_battle_options(data)
    assert data == before
