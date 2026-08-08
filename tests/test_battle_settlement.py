from __future__ import annotations

import importlib


def test_daily_settlement_confirmation_does_not_accept_mirror_statistics(monkeypatch) -> None:
    battle_module = importlib.import_module("tasks.battle.battle")

    class FakeBattleAuto:
        def find_language_text(self, zh_text, en_text) -> tuple[int, int] | bool:
            if zh_text == "战斗胜利":
                return 700, 700
            if zh_text == "确认":
                return 1400, 700
            return False

    monkeypatch.setattr(battle_module, "auto", FakeBattleAuto())

    assert battle_module._find_daily_battle_settlement_confirmation() == (1400, 700)
