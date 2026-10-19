"""Telecommands the station's uplink can encode, and the statuses of their life cycle.

The encoder itself lives in the grs-uplink service (domain/telecommands.py);
this is the operator-facing side of the same catalogue, so a typo in the form
is caught when the command is created and not minutes later, when the TC
Scheduler tries to transmit it. Unknown command types are still accepted —
other satellites and legacy rows use free text — but the operator is warned
that the uplink cannot encode them.

Statuses (uplink-pares-e-estados-fs2.md, section 3):

    pending -> queued -> sent -> response_received -> confirmed | failed
                              \\-> no_response

`sent` is written by the TC Scheduler from the radio's BURST_ACK; the last
three come from the satellite's answer, decoded on the downlink.
"""

from __future__ import annotations

from typing import Any, Mapping

STATUSES = (
    "pending", "queued", "sent", "response_received", "confirmed", "failed", "no_response",
)
IN_FLIGHT = ("sent", "response_received")
FINISHED = ("confirmed", "failed", "no_response")

# module_id_e in the OBDH2 satellite.h.
MODULE_IDS = {1: "battery heater", 2: "beacon", 3: "periodic telemetry"}

UPLINK_COMMANDS: dict[str, str] = {
    "PING": "Ping (0x40). No parameters. The satellite answers with a pong on VHF.",
    "ACTIVATE_MODULE": 'Activate Module (0x45). {"module_id": 1|2|3}. Answer: TC Feedback on UHF.',
    "DEACTIVATE_MODULE": 'Deactivate Module (0x46). {"module_id": 1|2|3}. Answer: TC Feedback on UHF.',
}


class InvalidTelecommand(ValueError):
    pass


def normalize_command_type(command_type: str) -> str:
    return command_type.strip().upper() if command_type.strip().upper() in UPLINK_COMMANDS \
        else command_type.strip()


def validate(command_type: str, parameters: Mapping[str, Any] | None) -> str | None:
    """Raises InvalidTelecommand for a known command with bad parameters.

    :return: a warning for a command type the uplink cannot encode, else None.
    """
    name = command_type.strip().upper()
    if name not in UPLINK_COMMANDS:
        return (f"'{command_type.strip()}' has no uplink encoding; the TC Scheduler will mark it "
                f"failed when it tries to transmit. Known: {', '.join(UPLINK_COMMANDS)}.")

    parameters = parameters or {}
    if not isinstance(parameters, Mapping):
        raise InvalidTelecommand("parameters must be a JSON object")
    if name == "PING":
        if parameters:
            raise InvalidTelecommand("PING takes no parameters")
        return None

    module = parameters.get("module_id")
    if isinstance(module, bool) or module not in MODULE_IDS:
        known = ", ".join(f"{key} ({label})" for key, label in MODULE_IDS.items())
        raise InvalidTelecommand(f"{name} needs module_id: {known}")
    return None
