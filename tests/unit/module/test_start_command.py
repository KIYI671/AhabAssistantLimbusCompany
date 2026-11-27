import pytest


@pytest.fixture(scope="module")
def sc(isolated_import):
    return isolated_import("module.start_command")


def test_plain_start(sc):
    request = sc.parse_start_command(["aalc", "start"])
    assert request.start and request.schedule_id is None and request.after_completion is None


def test_no_start(sc):
    assert sc.parse_start_command(["aalc"]).start is False
    # --exit 只在 start 之后生效
    assert sc.parse_start_command(["aalc", "--exit", "3"]).after_completion is None


@pytest.mark.parametrize("schedule_id", ["autodaily", "autodaily2", "autodaily_1a2b3c4d"])
def test_schedule(sc, schedule_id):
    request = sc.parse_start_command(["AALC.exe", "start", "--exit", schedule_id])
    assert request.start and request.schedule_id == schedule_id
    assert request.after_completion is None


def test_legacy_number(sc):
    request = sc.parse_start_command(["aalc", "start", "--exit", "3"])
    assert request.schedule_id is None
    assert request.after_completion.normalized() == ([], "shutdown")


def test_exit_without_value_defaults_to_exit_aalc(sc):
    request = sc.parse_start_command(["aalc", "start", "--exit"])
    assert request.after_completion.normalized() == (["exit_aalc"], "none")


def test_exit_out_of_range_means_nothing(sc):
    request = sc.parse_start_command(["aalc", "start", "--exit", "42"])
    assert request.after_completion.normalized() == ([], "none")
