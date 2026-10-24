"""Offline Qt/config checks. Qt events stay inside these widgets; no game APIs."""

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pydantic import ValidationError
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from qfluentwidgets import ExpandSettingCard, FluentIcon

ROOT = Path(__file__).resolve().parents[1]


def load_file(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schema = load_file("rabbit_config_schema", "module/config/config_typing.py")
ui = load_file("rabbit_options_ui", "app/rabbit_options.py")
APP = QApplication.instance() or QApplication([])


class TeamModelTests(unittest.TestCase):
    def test_original_team_defaults_remain_disabled(self):
        team = schema.TeamSetting(team_number=3)
        for key in (
            "rabbit_ego_enabled",
            "rabbit_event_exclusion_enabled",
            "rabbit_observe_enabled",
        ):
            self.assertFalse(getattr(team, key))
        self.assertEqual(team.rabbit_ego_rules, [])
        self.assertEqual(team.team_number, 3)

    def test_legacy_single_rule_migrates_without_enabling_feature(self):
        team = schema.TeamSetting(
            rabbit_ego_enabled=False, rabbit_ego_turn=7, rabbit_ego_name="空洞(le trou)", rabbit_ego_mode=0
        )
        self.assertFalse(team.rabbit_ego_enabled)
        self.assertEqual(
            [rule.model_dump() for rule in team.rabbit_ego_rules],
            [{"enabled": True, "turn": 7, "name": "空洞(le trou)", "mode": 0}],
        )

    def test_explicit_new_rules_or_empty_list_take_precedence_over_legacy(self):
        for rules in ([], [{"enabled": False, "turn": 4, "name": "新完整名称", "mode": 1}]):
            with self.subTest(rules=rules):
                team = schema.TeamSetting(rabbit_ego_name="旧完整名称", rabbit_ego_rules=rules)
                self.assertEqual([rule.model_dump() for rule in team.rabbit_ego_rules], rules)
        self.assertEqual(schema.TeamSetting(rabbit_ego_name="  ").rabbit_ego_rules, [])

    def test_ordered_disabled_rules_survive_serialization(self):
        rules = [
            {"enabled": False, "turn": 1, "name": "备用(全名)", "mode": 0},
            {"enabled": True, "turn": 1, "name": "优先全名", "mode": 1},
        ]
        team = schema.TeamSetting(
            rabbit_ego_enabled=False,
            rabbit_ego_rules=rules,
            rabbit_event_excluded=[1, 8],
            rabbit_observe_rules=[[1, 1, 3], [3, 2, 5]],
        )
        restored = schema.TeamSetting.model_validate_json(team.model_dump_json())
        self.assertEqual(restored.model_dump(), team.model_dump())
        self.assertEqual([r.model_dump() for r in restored.rabbit_ego_rules], rules)

    def test_rule_ranges_and_existing_selection_constraints(self):
        for rule in ({"turn": 0}, {"turn": 100}, {"mode": 2}):
            with self.subTest(rule=rule), self.assertRaises(ValidationError):
                schema.TeamSetting(rabbit_ego_rules=[rule])
        for fields in (
            {"rabbit_event_excluded": list(range(12))},
            {"rabbit_event_excluded": [-1]},
            {"rabbit_event_excluded": [1, 1]},
            {"rabbit_observe_rules": [[1, 0, 1]]},
            {"rabbit_observe_rules": [[6, 1, 1]]},
            {"rabbit_observe_rules": [[1, 1, 6]]},
            {"rabbit_observe_rules": [[1, 1, 1], [1, 2, 2]]},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                schema.TeamSetting(**fields)


class TeamOptionsWidgetTests(unittest.TestCase):
    def setUp(self):
        self.ego = ui.EgoReleaseOptions()
        self.events = ui.EventOptions()
        self.lock = ui.GiftLockOptions()
        self.advanced = ui.TeamAutomationOptions()
        self.observe = ui.ThemeObservationOptions()
        self.widgets = (self.ego, self.events, self.observe, self.lock, self.advanced)
        self.team = schema.TeamSetting()
        self.changes = []
        for widget in self.widgets:
            widget.load_settings(self.team)
            widget.changed.connect(self.changes.append)

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()

    def test_remaining_switches_are_independent_and_globals_absent(self):
        checks = {key: check for widget in self.widgets for key, check in widget.checks.items()}
        self.assertEqual(
            set(checks),
            {"rabbit_ego_enabled", "rabbit_event_exclusion_enabled", "rabbit_observe_enabled",
             "gift_lock_enabled", "battle_retry_limit_enabled"},
        )
        for key, check in checks.items():
            # Recovery is the sole new default-on option, per user instruction.
            check.setChecked(False)
        self.changes.clear()
        for key, check in checks.items():
            check.click()
            self.assertTrue(check.isChecked())
            self.assertTrue(all(not other.isChecked() for other_key, other in checks.items() if other_key != key))
            check.click()
        keys = {key for widget in self.widgets for key in widget.settings()}
        self.assertNotIn("rabbit_lower_chain", keys)
        self.assertNotIn("rabbit_animation_hold", keys)

    def test_multiple_ego_rule_objects_load_without_emitting_changes(self):
        team = schema.TeamSetting(
            rabbit_ego_enabled=True,
            rabbit_ego_rules=[
                {"enabled": True, "turn": 12, "name": "空洞(le trou)", "mode": 0},
                {"enabled": False, "turn": 12, "name": "备用完整名称", "mode": 1},
            ],
        )
        self.ego.load_settings(team)
        self.assertEqual(self.changes, [])
        self.assertEqual(self.ego.settings()["rabbit_ego_rules"], team.model_dump()["rabbit_ego_rules"])
        self.assertFalse(self.ego.rule_rows[1].name.isEnabled())
        self.ego.checks["rabbit_ego_enabled"].click()
        self.assertFalse(self.ego.body.isEnabled())
        self.assertEqual(self.ego.settings()["rabbit_ego_rules"], team.model_dump()["rabbit_ego_rules"])

    def test_rule_priority_moves_values_without_reconstructing_them(self):
        self.ego.checks["rabbit_ego_enabled"].click()
        self.ego.add_rule({"enabled": True, "turn": 1, "name": "第一完整名称", "mode": 1})
        self.ego.add_rule({"enabled": False, "turn": 1, "name": "第二完整名称", "mode": 0})
        second = self.ego.rule_rows[1]
        second.up_button.click()
        self.assertIs(self.ego.rule_rows[0], second)
        self.assertEqual(
            [rule["name"] for rule in self.ego.settings()["rabbit_ego_rules"]], ["第二完整名称", "第一完整名称"]
        )
        self.assertFalse(second.up_button.isEnabled())
        self.assertFalse(second.value()["enabled"])
        second.down_button.click()
        self.assertEqual(self.ego.rule_rows[1].value()["name"], "第二完整名称")
        self.ego.rule_rows[0].remove_button.click()
        self.assertEqual(len(self.ego.rule_rows), 1)
        self.assertEqual(self.ego.rule_rows[0].priority.text(), "优先级 1")

    def test_each_rule_can_be_disabled_and_added_again(self):
        self.ego.checks["rabbit_ego_enabled"].click()
        self.ego.add_rule_button.click()
        row = self.ego.rule_rows[0]
        row.name.setText("保存完整名称")
        row.turn.setValue(5)
        row.mode.setCurrentIndex(0)
        row.enabled.click()
        self.assertEqual(row.value(), {"enabled": False, "turn": 5, "name": "保存完整名称", "mode": 0})
        self.assertFalse(row.name.isEnabled())
        self.ego.add_rule_button.click()
        self.assertEqual(len(self.ego.rule_rows), 2)
        self.assertTrue(self.ego.rule_rows[1].enabled.isChecked())

    def test_event_cards_limit_and_no_formation_side_effects(self):
        self.events.checks["rabbit_event_exclusion_enabled"].click()
        for card in self.events.event_cards:
            card.click()
        self.assertEqual(self.events.settings()["rabbit_event_excluded"], list(range(11)))
        self.assertFalse(self.events.event_cards[-1].isChecked())
        self.assertEqual(self.team.chosen_sinners, [0] * 12)
        self.assertEqual(self.team.sinners_be_select, 0)
        self.assertFalse(any(any(key in change for key, _ in ui.SINNER_NAMES) for change in self.changes))
        self.events.event_cards[0].click()
        self.events.event_cards[-1].click()
        self.assertEqual(self.events.settings()["rabbit_event_excluded"], list(range(1, 12)))

    def test_multiple_observation_rules_and_duplicate_revert(self):
        self.observe.checks["rabbit_observe_enabled"].click()
        for _ in range(5):
            self.observe.add_rule_button.click()
        self.assertEqual([rule[0] for rule in self.observe.observation_rules()], [1, 2, 3, 4, 5])
        self.assertFalse(self.observe.add_rule_button.isEnabled())
        self.observe.rule_rows[2].row.setValue(2)
        self.observe.rule_rows[2].column.setValue(5)
        self.observe.rule_rows[2].floor.setValue(1)
        self.assertEqual(self.observe.observation_rules()[2], [3, 2, 5])
        self.observe.rule_rows[1].remove_button.click()
        self.assertTrue(self.observe.add_rule_button.isEnabled())

    def test_reload_clears_old_rows_without_cross_team_updates(self):
        self.ego.load_settings(schema.TeamSetting(rabbit_ego_rules=[{"name": "旧名称"}]))
        self.events.load_settings(schema.TeamSetting(rabbit_event_excluded=[0, 3]))
        self.observe.load_settings(schema.TeamSetting(rabbit_observe_rules=[[1, 1, 3], [2, 2, 2]]))
        self.assertEqual(self.changes, [])
        for widget in self.widgets:
            widget.load_settings(schema.TeamSetting())
        self.assertEqual(self.ego.settings()["rabbit_ego_rules"], [])
        self.assertEqual(self.events.settings()["rabbit_event_excluded"], [])
        self.assertEqual(self.observe.observation_rules(), [])


class TeamEditorIntegrationTests(unittest.TestCase):
    def test_separate_areas_save_ordered_rules_and_restore_all_values(self):
        from app.team_setting_card import TeamSettingCard
        from module.config import cfg

        with patch.object(cfg, "set_value") as save:
            editor = TeamSettingCard(1)
            editor.team_setting.rabbit_ego_enabled = False
            editor.team_setting.rabbit_ego_rules = []
            editor.read_settings()
            original_sinners = editor.team_setting.chosen_sinners[:]
            try:
                ego = editor.ego_release_module
                events = editor.event_options_module
                observe = editor.theme_observation_module
                self.assertFalse(hasattr(editor, "rabbit_options_layout"))
                ego.checks["rabbit_ego_enabled"].click()
                ego.add_rule({"enabled": True, "turn": 4, "name": "完整名称(le trou)", "mode": 0})
                ego.add_rule({"enabled": False, "turn": 4, "name": "备用完整名称", "mode": 1})
                ego.rule_rows[1].up_button.click()
                events.checks["rabbit_event_exclusion_enabled"].setChecked(True)
                events.event_cards[1].setChecked(True)
                observe.checks["rabbit_observe_enabled"].setChecked(True)
                observe.add_rule([3, 2, 5])
                editor.save_team_setting()
                saved = save.call_args.args[1]
                rules = saved.model_dump()["rabbit_ego_rules"]
                self.assertEqual([rule["name"] for rule in rules], ["备用完整名称", "完整名称(le trou)"])
                self.assertFalse(rules[0]["enabled"])
                self.assertEqual(rules[1]["turn"], 4)
                self.assertEqual(rules[1]["mode"], 0)
                self.assertTrue(all(hasattr(rule, "model_dump") for rule in saved.rabbit_ego_rules))
                self.assertIn(1, saved.rabbit_event_excluded)
                self.assertIn([3, 2, 5], saved.rabbit_observe_rules)
                self.assertEqual(saved.chosen_sinners, original_sinners)
                editor.team_setting = saved.model_copy(deep=True)
                editor.read_settings()
                self.assertEqual(ego.settings()["rabbit_ego_rules"], rules)
                self.assertEqual(events.settings()["rabbit_event_excluded"], saved.rabbit_event_excluded)
                self.assertEqual(observe.observation_rules(), saved.rabbit_observe_rules)
            finally:
                editor.disconnect_mediator()
                editor.close()
                editor.deleteLater()


class ExpandedCardsRegressionTests(unittest.TestCase):
    def create_expanded_card(self, component, key):
        window = QWidget()
        layout = QVBoxLayout(window)
        card = ExpandSettingCard(FluentIcon.SETTING, "Dynamic options", parent=window)
        widget = component(card)
        widget.load_settings(schema.TeamSetting(**{key: True}))
        card.viewLayout.addWidget(widget)
        layout.addWidget(card)
        layout.addStretch(1)
        window.resize(1050, 1500)
        window.show()
        APP.processEvents()
        card.setExpand(True)
        QTest.qWait(450)
        self.addCleanup(window.close)
        self.addCleanup(window.deleteLater)
        return card, widget

    def assert_full_height(self, card, widget):
        self.assertTrue(card.isExpand)
        required = card.card.height() + card.viewLayout.sizeHint().height()
        self.assertEqual(card.height(), required)
        bottom = widget.add_rule_button.mapTo(card, QPoint(0, widget.add_rule_button.height())).y()
        self.assertLessEqual(bottom, card.height(), "The Add button is clipped outside the expanded card")

    def test_dynamic_add_and_remove_resize_already_expanded_cards(self):
        for component, key in (
            (ui.EgoReleaseOptions, "rabbit_ego_enabled"),
            (ui.ThemeObservationOptions, "rabbit_observe_enabled"),
        ):
            with self.subTest(component=component.__name__):
                card, widget = self.create_expanded_card(component, key)
                initial_height = card.height()
                for _ in range(3):
                    widget.add_rule_button.click()
                QTest.qWait(60)
                self.assert_full_height(card, widget)
                self.assertGreater(card.height(), initial_height)
                for row in list(widget.rule_rows):
                    row.remove_button.click()
                QTest.qWait(60)
                self.assert_full_height(card, widget)
                self.assertEqual(card.height(), initial_height)

    def test_loading_rules_into_expanded_cards_updates_height_without_reopening(self):
        for component, key, values in (
            (
                ui.EgoReleaseOptions,
                "rabbit_ego_enabled",
                {"rabbit_ego_rules": [{"name": "一"}, {"name": "二"}, {"name": "三"}]},
            ),
            (
                ui.ThemeObservationOptions,
                "rabbit_observe_enabled",
                {"rabbit_observe_rules": [[1, 1, 3], [2, 2, 2], [3, 2, 5]]},
            ),
        ):
            with self.subTest(component=component.__name__):
                card, widget = self.create_expanded_card(component, key)
                initial_height = card.height()
                widget.load_settings(schema.TeamSetting(**{key: True, **values}))
                QTest.qWait(60)
                self.assert_full_height(card, widget)
                self.assertGreater(card.height(), initial_height)
                widget.load_settings(schema.TeamSetting(**{key: True}))
                QTest.qWait(60)
                self.assert_full_height(card, widget)
                self.assertEqual(card.height(), initial_height)

    def test_loading_and_removing_rules_never_force_collapsed_cards_open(self):
        for component, key, values in (
            (
                ui.EgoReleaseOptions,
                "rabbit_ego_enabled",
                {"rabbit_ego_rules": [{"name": "一"}, {"name": "二"}, {"name": "三"}]},
            ),
            (
                ui.ThemeObservationOptions,
                "rabbit_observe_enabled",
                {"rabbit_observe_rules": [[1, 1, 3], [2, 2, 2], [3, 2, 5]]},
            ),
        ):
            with self.subTest(component=component.__name__):
                card, widget = self.create_expanded_card(component, key)
                card.setExpand(False)
                QTest.qWait(450)
                collapsed_height = card.height()
                widget.load_settings(schema.TeamSetting(**{key: True, **values}))
                QTest.qWait(60)
                self.assertFalse(card.isExpand)
                self.assertEqual(card.height(), collapsed_height)
                self.assertEqual(card.spaceWidget.height(), card.viewLayout.sizeHint().height())
                widget.rule_rows[0].remove_button.click()
                QTest.qWait(60)
                self.assertFalse(card.isExpand)
                self.assertEqual(card.height(), collapsed_height)
                self.assertEqual(card.spaceWidget.height(), card.viewLayout.sizeHint().height())
                card.setExpand(True)
                QTest.qWait(450)
                self.assert_full_height(card, widget)


if __name__ == "__main__":
    unittest.main()
