"""The uplink catalogue the form validates against, and the status CHECK migration.

No database: the migration's SQL is checked as text; applying it is covered
by the station's end-to-end run.
"""
import pytest

from app.database.migrations import status_check_sql
from app.services.uplink_catalog import (
    FINISHED, IN_FLIGHT, STATUSES, InvalidTelecommand, normalize_command_type, validate,
)


def test_statuses_cover_the_uplink_life_cycle():
    assert STATUSES == ("pending", "queued", "sent", "response_received", "confirmed",
                        "failed", "no_response")
    assert set(IN_FLIGHT) | set(FINISHED) | {"pending", "queued"} == set(STATUSES)
    # VARCHAR(20) in the table
    assert max(len(status) for status in STATUSES) <= 20


def test_check_constraint_lists_every_status():
    sql = status_check_sql()
    assert all(f"'{status}'" in sql for status in STATUSES)


@pytest.mark.parametrize("command_type, parameters", [
    ("PING", {}),
    ("ping", None),
    ("ACTIVATE_MODULE", {"module_id": 3}),
    ("DEACTIVATE_MODULE", {"module_id": 1}),
])
def test_known_commands_with_valid_parameters(command_type, parameters):
    assert validate(command_type, parameters) is None


@pytest.mark.parametrize("command_type, parameters", [
    ("PING", {"payload": "0x55AA"}),
    ("ACTIVATE_MODULE", {}),
    ("ACTIVATE_MODULE", {"module_id": 9}),
    ("ACTIVATE_MODULE", {"module_id": True}),
    ("DEACTIVATE_MODULE", ["module_id", 1]),
])
def test_known_commands_with_bad_parameters_are_refused(command_type, parameters):
    with pytest.raises(InvalidTelecommand):
        validate(command_type, parameters)


def test_unknown_command_is_accepted_with_a_warning():
    warning = validate("ORBIT_ADJUST", {"dv": 1})
    assert "no uplink encoding" in warning


def test_known_command_types_are_normalized_unknown_kept():
    assert normalize_command_type(" ping ") == "PING"
    assert normalize_command_type(" Orbit_Adjust ") == "Orbit_Adjust"
