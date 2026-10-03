"""Bounded local Cppcheck configuration and exact native sanitizer policy inputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.models import string_list
from score_sw_fabric.assurance.models import nonempty, stable_id, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.controls import selected_bytes, yaml_tree

CPPCHECK_FIELDS = {
    "id",
    "status",
    "standard",
    "language",
    "enable",
    "platform",
    "max_configs",
    "error_exitcode",
    "xml_version",
}
SANITIZER_FIELDS = {
    "id",
    "status",
    "mode",
    "feature",
    "native_features",
    "native_runtime",
    "native_suppressions",
}
CPPCHECK_CATEGORIES = {
    "warning",
    "style",
    "performance",
    "portability",
    "information",
    "missingInclude",
}


def _flags(text: str, name: str) -> list[str]:
    match = re.search(
        r'cc_args\(\s*name\s*=\s*"' + re.escape(name) + r'",.*?args\s*=\s*\[(.*?)\]', text, re.S
    )
    if not match:
        raise InputError(
            "NATIVE_POLICY_UNSUPPORTED", "Native compiler argument declaration missing"
        )
    values = re.findall(r'"([^"\n]+)"', match[1])
    if not values or any(re.fullmatch(r"-[A-Za-z0-9=+_,.-]+", value) is None for value in values):
        raise InputError("NATIVE_POLICY_UNSUPPORTED", "Unsupported native compiler argument")
    return values


def load_configuration(
    data: bytes, base: Path, profile: dict[str, Any], adapter: str
) -> tuple[dict[str, Any], dict[str, bytes], list[Path]]:
    if adapter == "cppcheck":
        c = version(
            yaml_tree(data, "/config"),
            "quality_cppcheck_configuration",
            CPPCHECK_FIELDS,
            "/config",
        )
        stable_id(c["id"], "/config/id")
        nonempty(c["status"], "/config/status", max_length=64)
        categories = string_list(c["enable"], "/enable", limit=6, length=64)
        if (
            not categories
            or len(set(categories)) != len(categories)
            or set(categories) - CPPCHECK_CATEGORIES
            or c["standard"] != "c++17"
            or c["language"] != "c++"
            or c["platform"] != "unix64"
            or type(c["max_configs"]) is not int
            or not 1 <= c["max_configs"] <= 12
            or type(c["error_exitcode"]) is not int
            or c["error_exitcode"] != 2
            or type(c["xml_version"]) is not int
            or c["xml_version"] != 2
        ):
            raise InputError("CONFIG_UNSUPPORTED", "Unresearched or unsafe Cppcheck configuration")
        return c, {}, []
    c = version(
        yaml_tree(data, "/config"), "quality_sanitizer_configuration", SANITIZER_FIELDS, "/config"
    )
    stable_id(c["id"], "/config/id")
    nonempty(c["status"], "/config/status", max_length=64)
    if c["mode"] != adapter or c["feature"] != ("asan" if adapter == "asan" else "ubsan_gcc"):
        raise InputError(
            "CONFIG_UNSUPPORTED", "Mode/feature differs from separate GCC sanitizer selection"
        )
    assets: dict[str, bytes] = {}
    paths = []
    for key, ident in [
        ("native_features", "sanitizer_features"),
        ("native_runtime", adapter + "_runtime"),
        ("native_suppressions", adapter + "_suppressions"),
    ]:
        path, content = selected_bytes(base, c[key], f"/{key}")
        if len(content) > 1024 * 1024:
            raise InputError("LIMIT_EXCEEDED", "Native policy asset exceeds 1 MiB")
        source = next((s for s in profile["native_sources"] if s["id"] == ident), None)
        if source is None or source["sha256"] != c[key]["sha256"]:
            raise InputError(
                "NATIVE_POLICY_IDENTITY_MISMATCH", "Asset is not the selected native source"
            )
        assets[key] = content
        paths.append(path)
    try:
        text = assets["native_features"].decode("utf-8")
        runtime = assets["native_runtime"].decode("utf-8").strip()
        suppression = assets["native_suppressions"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError("NATIVE_POLICY_UNSUPPORTED", "Native policy is not UTF-8") from exc
    runtime_name = "ASAN_OPTIONS" if adapter == "asan" else "UBSAN_OPTIONS"
    if (
        not runtime.startswith(runtime_name + "=")
        or "\n" in runtime
        or runtime.count("%ROOT%") != 1
        or f"suppressions=%ROOT%sanitizers/suppressions/{adapter}.supp" not in runtime
    ):
        raise InputError("NATIVE_POLICY_UNSUPPORTED", "Unknown native runtime template")
    compile_name = "asan_compile_args" if adapter == "asan" else "ubsan_compile_args"
    link_name = "asan_link_args" if adapter == "asan" else "ubsan_link_args_base"
    settings = {
        **c,
        "compile_flags": [*_flags(text, "debug_symbols_args"), *_flags(text, compile_name)],
        "link_flags": _flags(text, link_name),
        "runtime_name": runtime_name,
        "runtime_template": runtime.split("=", 1)[1],
        "suppression_rules": [
            line.strip()
            for line in suppression.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ],
    }
    return settings, assets, paths
