"""Pinned profile and local toolchain checks."""

from __future__ import annotations

import pytest

from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.verification.profile import load_profile, load_toolchain, verify_toolchain
from tests.verification_support import PROFILE, TOOLCHAIN


def test_profiles_and_local_toolchain() -> None:
    profile = load_profile(PROFILE.read_bytes())
    toolchain = load_toolchain(TOOLCHAIN.read_bytes())
    assert len(profile["inspection_checklist"]) == 8
    assert profile["loop"]["max_attempts"] == 3
    assert verify_toolchain(toolchain)["compiler"]["sha256"] == toolchain["compiler"]["sha256"]
    toolchain["compiler"]["sha256"] = "0" * 64
    with pytest.raises(InputError) as error:
        verify_toolchain(toolchain)
    assert error.value.code == "TOOLCHAIN_MISMATCH"
