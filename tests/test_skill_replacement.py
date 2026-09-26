"""Exercise shop decisions without starting the GUI, OCR or game input drivers."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def shop_env():
    source = Path(__file__).resolve().parents[1] / "tasks/mirror/in_shop.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    shop = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Shop")
    names = {"_replace_selected_skill", "id_skill_replacement", "selected_id_skill_replacement"}
    shop.body = [node for node in shop.body if isinstance(node, ast.FunctionDef) and node.name in names]
    auto = Mock()
    namespace = {
        "auto": auto,
        "sleep": Mock(),
        "retry": Mock(return_value=True),
        "cfg": SimpleNamespace(set_win_size=1440),
        "all_sinners_name": ["Yi Sang"],
        "all_sinners_name_zh": ["李箱"],
    }
    exec(compile(ast.Module(body=[shop], type_ignores=[]), str(source), "exec"), namespace)
    instance = namespace["Shop"]()
    instance.RestartGame = RuntimeError
    instance.skill_replacement_select = 0
    instance.sinner_team = [1]
    return instance, auto, namespace


COINS = [(300, 20), (100, 20), (200, 20)]


@pytest.mark.parametrize("mode,x", [(0, 300), (1, 200), (2, 100)])
def test_existing_modes_keep_their_column(shop_env, mode, x):
    shop, auto, _ = shop_env
    shop.skill_replacement_mode = mode
    auto.find_element.return_value = COINS
    shop._replace_selected_skill()
    auto.mouse_click.assert_called_once_with(x, 20)


@pytest.mark.parametrize("mode,expected", [(3, [(200, 20), (300, 20)]), (4, [(300, 20), (200, 20)])])
def test_all_to_three_tries_both_without_one_to_two(shop_env, mode, expected):
    shop, auto, _ = shop_env
    shop.skill_replacement_mode = mode
    auto.find_element.side_effect = [COINS, COINS]
    shop._replace_selected_skill()
    assert [call.args for call in auto.mouse_click.call_args_list] == expected
    assert all(call.kwargs["take_screenshot"] for call in auto.find_element.call_args_list)


@pytest.mark.parametrize("mode,x", [(3, 200), (4, 300)])
def test_completed_purchase_stops_before_stale_click(shop_env, mode, x):
    shop, auto, _ = shop_env
    shop.skill_replacement_mode = mode
    auto.find_element.side_effect = [COINS, []]
    shop._replace_selected_skill()
    auto.mouse_click.assert_called_once_with(x, 20)


@pytest.mark.parametrize("coins", [None, [], [(100, 20)], COINS[:2]])
@pytest.mark.parametrize("mode", [3, 4])
def test_incomplete_recognition_does_not_click(shop_env, coins, mode):
    shop, auto, _ = shop_env
    shop.skill_replacement_mode = mode
    auto.find_element.return_value = coins
    shop._replace_selected_skill()
    auto.mouse_click.assert_not_called()
    auto.click_element.assert_not_called()


@pytest.mark.parametrize("mode,x", [(3, 200), (4, 300)])
def test_game_restart_is_preserved(shop_env, mode, x):
    shop, auto, namespace = shop_env
    shop.skill_replacement_mode = mode
    auto.find_element.return_value = COINS
    namespace["retry"].return_value = False
    with pytest.raises(RuntimeError):
        shop._replace_selected_skill()
    auto.mouse_click.assert_called_once_with(x, 20)


@pytest.mark.parametrize("method", ["id_skill_replacement", "selected_id_skill_replacement"])
@pytest.mark.parametrize("mode,expected", [(3, [(200, 20), (300, 20)]), (4, [(300, 20), (200, 20)])])
def test_both_shop_paths_use_all_to_three(shop_env, method, mode, expected):
    shop, auto, _ = shop_env
    shop.skill_replacement_mode = mode
    if method == "id_skill_replacement":
        auto.find_element.side_effect = [(500, 500), COINS, COINS]
        auto.find_language_text.return_value = True
    else:
        auto.find_element.side_effect = [False, COINS, COINS]
    getattr(shop, method)("shop-entry.png")
    assert [call.args for call in auto.mouse_click.call_args_list][-2:] == expected
