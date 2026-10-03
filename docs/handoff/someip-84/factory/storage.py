"""Compatibility imports for prepared factory scripts; policy is fabric-wide."""

from score_sw_fabric.storage import (  # noqa: F401
    CONFIG,
    NATIVE_FILESYSTEMS,
    bridge_mount,
    discover_ssds,
    private_server_root,
    select_storage,
    validate_run_root,
)
from score_sw_fabric.storage import new_run_root as _new_run_root


def new_run_root():
    return _new_run_root(prefix="score-someip84-factory-")
