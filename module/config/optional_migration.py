"""Move optional settings without overwriting explicit new-format choices."""


from copy import deepcopy


def migrate_global_battle_options(data, default_teams=None):
    for global_key, legacy_key in (
        ("mirror_lower_chain", "rabbit_lower_chain"),
    ):
        if global_key not in data:
            data[global_key] = any(
                bool(team.get(legacy_key, False)) if isinstance(team, dict) else bool(getattr(team, legacy_key, False))
                for team in (data.get("teams") or {}).values()
            )
    if "battle_speed_hold" not in data:
        legacy_animation = data.get("ego_animation_hold")
        if legacy_animation is None:
            legacy_animation = any(
                bool(team.get("rabbit_animation_hold", False)) if isinstance(team, dict)
                else bool(getattr(team, "rabbit_animation_hold", False))
                for team in (data.get("teams") or {}).values()
            )
        data["battle_speed_hold"] = bool(legacy_animation or data.get("combat_speed_hold", False))
    legacy_floor = data.get("floor_3_exit")
    if legacy_floor is not None:
        if "teams" not in data and default_teams is not None:
            data["teams"] = deepcopy(default_teams)
            # Example defaults are not explicit user choices.
            for team in data["teams"].values():
                team["mirror_floor_limit"] = 3 if legacy_floor else 5
    for team in (data.get("teams") or {}).values():
        if isinstance(team, dict):
            team.pop("route_repeat_recovery", None)
            old_value = team.pop("floor_3_exit", legacy_floor)
            if old_value is not None:
                team.setdefault("mirror_floor_limit", 3 if old_value else 5)
    for key in ("ego_animation_hold", "combat_speed_hold", "floor_3_exit"):
        data.pop(key, None)
    return data
