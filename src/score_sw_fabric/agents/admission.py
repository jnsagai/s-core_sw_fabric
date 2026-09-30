"""Pre-call model capability, fallback and budget admission; never authorizes a live call."""

from __future__ import annotations

import hashlib
import math
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from score_sw_fabric.agents.lock import load_lock
from score_sw_fabric.agents.models import (
    READINESS,
    input_file,
    load_request,
    protected_roots,
    yaml_file,
)
from score_sw_fabric.agents.roles import BUDGET_CEILINGS, validate_role
from score_sw_fabric.assurance.models import exact, nonempty, seal, sha, stable_id, version
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.runtime.request import parse_json, parse_yaml

ADMIT_FIELDS = {"lock", "role", "model_profiles", "catalogue", "ledger", "call", "protected_roots"}
PROFILES_FIELDS = {"id", "status", "live_calls", "catalogue", "profiles"}
PROFILE_FIELDS = {
    "id",
    "provider",
    "model",
    "reasoning_effort",
    "requires_tools",
    "max_output_tokens",
    "max_context_tokens",
    "timeout_seconds",
    "data_destination",
    "fallbacks",
}
LEDGER_FIELDS = {"role_id", "entries"}
ENTRY_FIELDS = {
    "call_id",
    "attempt",
    "profile",
    "usage_origin",
    "input_tokens",
    "output_tokens",
    "cost_microusd",
    "wall_seconds",
}
USAGE = ("input_tokens", "output_tokens", "cost_microusd", "wall_seconds")
ATTEMPTS = frozenset({"initial", "retry", "correction_visit", "fallback"})
MAX_PAGES = 100
MAX_ROWS = 10_000
MAX_ENTRIES = 10_000
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _positive(value: Any, pointer: str, ceiling: int) -> int:
    if type(value) is not int or not 0 < value <= ceiling:
        raise InputError(
            "LIMIT_EXCEEDED", f"Expected a positive bounded integer at {pointer}", pointer
        )
    return value


def _price(value: Any, pointer: str) -> str | None:
    """Catalogue price as exact decimal text, or None when the runtime reports none."""
    if value is None:
        return None
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise InputError("CATALOGUE_FORMAT", f"Invalid price at {pointer}", pointer)
    return str(Decimal(str(value)))


def _limit(value: Any, pointer: str) -> int | None:
    """Catalogue limit; the runtime reports unknown limits as null or 0."""
    if value is None or value == 0:
        return None
    return _positive(value, pointer, 1 << 40)


def load_catalogue(pages: list[bytes]) -> dict[tuple[str, str], dict[str, Any]]:
    """Validate raw `GET /api/v1/models` pages as one complete, unique offering catalogue."""
    if not pages or len(pages) > MAX_PAGES:
        raise InputError(
            "CATALOGUE_INCOMPLETE", "Expected 1-100 catalogue pages", "/catalogue/pages"
        )
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for index, data in enumerate(pages):
        pointer = f"/catalogue/pages/{index}"
        page = parse_json(data, pointer)
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise InputError("CATALOGUE_FORMAT", "Page lacks data", pointer)
        meta = page.get("meta")
        has_more = meta.get("has_more") if isinstance(meta, dict) else None
        if has_more is not (index < len(pages) - 1):
            raise InputError(
                "CATALOGUE_INCOMPLETE", "Pages do not end the catalogue exactly", pointer
            )
        for position, raw in enumerate(page["data"]):
            row_pointer = f"{pointer}/data/{position}"
            if not isinstance(raw, dict):
                raise InputError("CATALOGUE_FORMAT", "Row is not an object", row_pointer)
            try:
                key = (nonempty(raw["provider"], row_pointer), nonempty(raw["id"], row_pointer))
                limits = raw["limits"]
                row = {
                    "provider": key[0],
                    "id": key[1],
                    "aliases": [
                        nonempty(item, row_pointer, max_length=128) for item in raw["aliases"]
                    ],
                    "context_window": _limit(limits["context_window"], row_pointer),
                    "max_output": _limit(limits["max_output"], row_pointer),
                    "tools": raw["features"]["tools"] is True,
                    "reasoning": raw["features"]["reasoning"] is True,
                    "reasoning_effort": [
                        nonempty(item, row_pointer, max_length=32)
                        for item in raw["controls"]["reasoning_effort"]
                    ],
                    "input_cost_per_mtok": _price(raw["costs"]["input_cost_per_mtok"], row_pointer),
                    "output_cost_per_mtok": _price(
                        raw["costs"]["output_cost_per_mtok"], row_pointer
                    ),
                    "configured": raw["configured"] is True,
                }
            except (KeyError, TypeError) as exc:
                raise InputError(
                    "CATALOGUE_FORMAT", "Row lacks required fields", row_pointer
                ) from exc
            if key in rows:
                raise InputError(
                    "CATALOGUE_FORMAT", "Duplicate provider/model offering", row_pointer
                )
            rows[key] = row
            if len(rows) > MAX_ROWS:
                raise InputError("LIMIT_EXCEEDED", "Catalogue exceeds 10,000 offerings", pointer)
    return rows


def validate_profiles(value: Any) -> dict[str, Any]:
    record = version(value, "agent_model_profiles", PROFILES_FIELDS, "/agent_model_profiles")
    stable_id(record["id"], "/id")
    nonempty(record["status"], "/status", max_length=64)
    if record["live_calls"] != "disabled":
        raise InputError(
            "LIVE_CALLS_UNAUTHORIZED", "Live model calls are not authorized", "/live_calls"
        )
    catalogue = exact(record["catalogue"], {"runtime_commit", "pages_sha256"}, "/catalogue")
    if not isinstance(catalogue["runtime_commit"], str) or not COMMIT.fullmatch(
        catalogue["runtime_commit"]
    ):
        raise InputError(
            "HASH_FORMAT", "Expected a full runtime commit", "/catalogue/runtime_commit"
        )
    if not isinstance(catalogue["pages_sha256"], list) or not catalogue["pages_sha256"]:
        raise InputError("FIELD_TYPE", "Expected page digests", "/catalogue/pages_sha256")
    for index, item in enumerate(catalogue["pages_sha256"]):
        sha(item, f"/catalogue/pages_sha256/{index}")
    profiles = record["profiles"]
    if not isinstance(profiles, list) or not profiles or len(profiles) > 100:
        raise InputError("LIMIT_EXCEEDED", "Expected 1-100 model profiles", "/profiles")
    ids = set()
    for index, raw in enumerate(profiles):
        pointer = f"/profiles/{index}"
        item = exact(raw, PROFILE_FIELDS, pointer)
        ids.add(stable_id(item["id"], pointer + "/id"))
        nonempty(item["provider"], pointer + "/provider", max_length=64)
        nonempty(item["model"], pointer + "/model", max_length=128)
        if item["reasoning_effort"] is not None:
            nonempty(item["reasoning_effort"], pointer + "/reasoning_effort", max_length=32)
        if not isinstance(item["requires_tools"], bool):
            raise InputError("FIELD_TYPE", "requires_tools must be boolean", pointer)
        _positive(item["max_output_tokens"], pointer + "/max_output_tokens", 10_000_000)
        _positive(item["max_context_tokens"], pointer + "/max_context_tokens", 100_000_000)
        _positive(item["timeout_seconds"], pointer + "/timeout_seconds", 24 * 3600)
        stable_id(item["data_destination"], pointer + "/data_destination")
        if not isinstance(item["fallbacks"], list) or len(item["fallbacks"]) > 8:
            raise InputError("LIMIT_EXCEEDED", "Too many fallbacks", pointer + "/fallbacks")
        for position, fallback in enumerate(item["fallbacks"]):
            entry = exact(
                fallback, {"profile", "allow_higher_price"}, f"{pointer}/fallbacks/{position}"
            )
            if not isinstance(entry["allow_higher_price"], bool) or entry["profile"] == item["id"]:
                raise InputError(
                    "FIELD_TYPE", "Invalid fallback entry", f"{pointer}/fallbacks/{position}"
                )
    if len(ids) != len(profiles):
        raise InputError("DUPLICATE_ID", "Duplicate model profile", "/profiles")
    for index, item in enumerate(profiles):
        for fallback in item["fallbacks"]:
            if fallback["profile"] not in ids:
                raise InputError(
                    "MODEL_PROFILE_UNKNOWN", "Fallback profile is undefined", f"/profiles/{index}"
                )
    return record


def validate_ledger(value: Any, role_id: str) -> list[dict[str, Any]]:
    ledger = version(value, "agent_budget_ledger", LEDGER_FIELDS, "/agent_budget_ledger")
    if ledger["role_id"] != role_id:
        raise InputError("LEDGER_MISMATCH", "Ledger belongs to another role", "/ledger/role_id")
    entries = ledger["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise InputError("LIMIT_EXCEEDED", "Too many ledger entries", "/ledger/entries")
    ids = set()
    for index, raw in enumerate(entries):
        pointer = f"/ledger/entries/{index}"
        entry = exact(raw, ENTRY_FIELDS, pointer)
        ids.add(stable_id(entry["call_id"], pointer + "/call_id"))
        if entry["attempt"] not in ATTEMPTS:
            raise InputError("FIELD_ENUM", "Unknown attempt kind", pointer + "/attempt")
        stable_id(entry["profile"], pointer + "/profile")
        if entry["usage_origin"] not in {"runtime_observation", "unknown"}:
            raise InputError("FIELD_ENUM", "Unknown usage origin", pointer + "/usage_origin")
        for name in USAGE:
            item = entry[name]
            if item is None:
                continue
            if entry["usage_origin"] == "unknown" or type(item) is not int or item < 0:
                raise InputError(
                    "USAGE_FORMAT", "Unknown usage must be null; known usage an integer", pointer
                )
    if len(ids) != len(entries):
        raise InputError("DUPLICATE_ID", "Duplicate ledger call", "/ledger/entries")
    return entries


def estimate_cost(offering: dict[str, Any], input_tokens: int, output_tokens: int) -> int | None:
    """Micro-USD upper estimate: USD per million tokens equals micro-USD per token."""
    if offering["input_cost_per_mtok"] is None or offering["output_cost_per_mtok"] is None:
        return None
    total = Decimal(input_tokens) * Decimal(offering["input_cost_per_mtok"]) + Decimal(
        output_tokens
    ) * Decimal(offering["output_cost_per_mtok"])
    return int(total.to_integral_value(rounding="ROUND_CEILING"))


def _capability(
    profile: dict[str, Any],
    catalogue: dict[tuple[str, str], dict[str, Any]],
    input_tokens: int,
    reasons: list[dict[str, str]],
) -> dict[str, Any] | None:
    key = (profile["provider"], profile["model"])
    offering = catalogue.get(key)
    if offering is None:
        canonical = next(
            (
                row
                for row in catalogue.values()
                if row["provider"] == key[0] and key[1] in row["aliases"]
            ),
            None,
        )
        if canonical is not None:
            reasons.append(
                {"code": "MODEL_ALIAS", "detail": f"{key[1]} is an alias of {canonical['id']}"}
            )
        else:
            reasons.append({"code": "MODEL_UNKNOWN", "detail": f"{key[0]}/{key[1]}"})
        return None
    if profile["requires_tools"] and not offering["tools"]:
        reasons.append({"code": "TOOLS_UNSUPPORTED", "detail": profile["id"]})
    effort = profile["reasoning_effort"]
    if effort is not None and effort not in offering["reasoning_effort"]:
        reasons.append({"code": "REASONING_UNSUPPORTED", "detail": f"{profile['id']}: {effort}"})
    for field, name, code in (
        ("max_output", "max_output_tokens", "OUTPUT_LIMIT"),
        ("context_window", "max_context_tokens", "CONTEXT_LIMIT"),
    ):
        if offering[field] is None:
            reasons.append({"code": "LIMIT_UNKNOWN", "detail": f"{profile['id']}: {field}"})
        elif profile[name] > offering[field]:
            reasons.append({"code": code, "detail": f"{profile['id']}: profile exceeds offering"})
    for field in ("input_cost_per_mtok", "output_cost_per_mtok"):
        if offering[field] is None:
            reasons.append({"code": "PRICE_UNKNOWN", "detail": f"{profile['id']}: {field}"})
    if input_tokens + profile["max_output_tokens"] > profile["max_context_tokens"]:
        reasons.append(
            {"code": "CONTEXT_LIMIT", "detail": f"{profile['id']}: call exceeds profile"}
        )
    return offering


def admit(request_path: Path) -> tuple[int, dict[str, Any], list[Path], list[Path]]:
    record, base = load_request(request_path, "agent_admit_request", ADMIT_FIELDS)
    lock_path, lock_bytes = input_file(base, record["lock"], "/lock")
    role_path, role_bytes, raw_role = yaml_file(base, record["role"], "/role")
    role = validate_role(raw_role, load_lock(lock_bytes))
    profiles_path, profiles_bytes, raw_profiles = yaml_file(
        base, record["model_profiles"], "/model_profiles"
    )
    profiles = validate_profiles(raw_profiles)
    catalogue_record = exact(
        record["catalogue"], {"runtime_commit", "executable_sha256", "pages"}, "/catalogue"
    )
    sha(catalogue_record["executable_sha256"], "/catalogue/executable_sha256")
    if catalogue_record["runtime_commit"] != profiles["catalogue"]["runtime_commit"]:
        raise InputError(
            "CATALOGUE_MISMATCH", "Profiles were reviewed on another runtime", "/catalogue"
        )
    raw_pages = catalogue_record["pages"]
    if not isinstance(raw_pages, list) or len(raw_pages) > MAX_PAGES:
        raise InputError("LIMIT_EXCEEDED", "Too many catalogue pages", "/catalogue/pages")
    pages = [
        input_file(base, item, f"/catalogue/pages/{index}") for index, item in enumerate(raw_pages)
    ]
    page_digests = [hashlib.sha256(data).hexdigest() for _, data in pages]
    if page_digests != profiles["catalogue"]["pages_sha256"]:
        raise InputError(
            "CATALOGUE_MISMATCH", "Profiles were reviewed on other catalogue pages", "/catalogue"
        )
    catalogue = load_catalogue([data for _, data in pages])
    ledger_path, ledger_bytes = input_file(base, record["ledger"], "/ledger")
    entries = validate_ledger(parse_yaml(ledger_bytes, "/ledger"), role["id"])
    protected = protected_roots(base, record["protected_roots"], "/protected_roots")
    call = exact(
        record["call"], {"call_id", "attempt", "profile", "estimated_input_tokens"}, "/call"
    )
    stable_id(call["call_id"], "/call/call_id")
    if call["call_id"] in {entry["call_id"] for entry in entries}:
        raise InputError("DUPLICATE_ID", "Call is already in the ledger", "/call/call_id")
    if call["attempt"] not in ATTEMPTS:
        raise InputError("FIELD_ENUM", "Unknown attempt kind", "/call/attempt")
    input_tokens = _positive(
        call["estimated_input_tokens"], "/call/estimated_input_tokens", 100_000_000
    )
    by_id = {item["id"]: item for item in profiles["profiles"]}
    if role["model_profile"] not in by_id:
        raise InputError("MODEL_PROFILE_UNKNOWN", "Role model profile is undefined", "/role")
    if call["profile"] not in by_id:
        raise InputError("MODEL_PROFILE_UNKNOWN", "Call profile is undefined", "/call/profile")
    primary = by_id[role["model_profile"]]
    selected = by_id[call["profile"]]
    reasons: list[dict[str, str]] = []
    primary_offering = _capability(primary, catalogue, input_tokens, [])
    offering = _capability(selected, catalogue, input_tokens, reasons)
    if call["attempt"] == "fallback":
        allowed = next(
            (item for item in primary["fallbacks"] if item["profile"] == selected["id"]), None
        )
        if allowed is None:
            reasons.append({"code": "FALLBACK_NOT_ALLOWLISTED", "detail": selected["id"]})
        if selected["data_destination"] != primary["data_destination"]:
            reasons.append({"code": "FALLBACK_DESTINATION", "detail": selected["data_destination"]})
        if (primary["requires_tools"] and not selected["requires_tools"]) or (
            primary["reasoning_effort"] is None
        ) != (selected["reasoning_effort"] is None):
            reasons.append({"code": "FALLBACK_INCOMPATIBLE", "detail": selected["id"]})
        if (
            allowed is not None
            and not allowed["allow_higher_price"]
            and offering is not None
            and primary_offering is not None
            and any(
                offering[name] is None
                or primary_offering[name] is None
                or Decimal(offering[name]) > Decimal(primary_offering[name])
                for name in ("input_cost_per_mtok", "output_cost_per_mtok")
            )
        ):
            reasons.append({"code": "FALLBACK_PRICE_ESCALATION", "detail": selected["id"]})
    elif selected["id"] != primary["id"]:
        reasons.append({"code": "PROFILE_NOT_ROLE", "detail": selected["id"]})
    if selected["data_destination"] not in role["data_destinations"]:
        reasons.append({"code": "DESTINATION_NOT_ALLOWED", "detail": selected["data_destination"]})
    counts = {kind: sum(entry["attempt"] == kind for entry in entries) for kind in ATTEMPTS}
    if call["attempt"] == "retry" and counts["retry"] + 1 > role["retry_limit"]:
        reasons.append({"code": "RETRY_LIMIT", "detail": str(role["retry_limit"])})
    visits = role["loopback"]["max_correction_visits"]
    if call["attempt"] == "correction_visit" and counts["correction_visit"] + 1 > visits:
        reasons.append({"code": "VISIT_LIMIT", "detail": str(visits)})
    budget = role["budget"]
    used: dict[str, int | None] = {"calls": len(entries)}
    for name in USAGE:
        values = [entry[name] for entry in entries]
        used[name] = None if any(item is None for item in values) else sum(values)
    estimate = {
        "input_tokens": input_tokens,
        "output_tokens": selected["max_output_tokens"],
        "cost_microusd": None
        if offering is None
        else estimate_cost(offering, input_tokens, selected["max_output_tokens"]),
        "wall_seconds": selected["timeout_seconds"],
        "calls": 1,
    }
    remaining: dict[str, int | None] = {}
    for name in BUDGET_CEILINGS:
        spent = used[name]
        if spent is None:
            remaining[name] = None
            reasons.append({"code": "USAGE_UNKNOWN", "detail": name})
            continue
        remaining[name] = budget[name] - spent
        needed = estimate[name]
        if name == "calls" and spent + 1 > budget[name]:
            reasons.append({"code": "CALL_LIMIT", "detail": str(budget[name])})
        elif needed is not None and name != "calls" and needed > remaining[name]:
            reasons.append({"code": "BUDGET_EXHAUSTED", "detail": name})
    output = {
        "schema_version": 1,
        "kind": "agent_admission",
        "role": {"id": role["id"], "sha256": hashlib.sha256(role_bytes).hexdigest()},
        "model_profiles": {
            "id": profiles["id"],
            "sha256": hashlib.sha256(profiles_bytes).hexdigest(),
        },
        "catalogue": {
            "runtime_commit": catalogue_record["runtime_commit"],
            "executable_sha256": catalogue_record["executable_sha256"],
            "pages_sha256": page_digests,
            "offerings": len(catalogue),
        },
        "ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "call": call,
        "profile": selected,
        "offering": offering,
        "estimate": estimate,
        "used": used,
        "remaining": remaining,
        "decision": "refused" if reasons else "admissible",
        "reasons": reasons,
        "call_authorized": False,
        "provider_configured": bool(offering and offering["configured"]),
        "engineering_readiness": READINESS,
        "limitations": [
            "Admission is a deterministic pre-call check; no live model call is authorized in 007.",
            "Costs are catalogue estimates using the maximum output; provider charges may differ.",
            "Usage from a real call must come from runtime observations, never agent claims.",
        ],
    }
    return (
        1 if reasons else 0,
        seal(output),
        [lock_path, role_path, profiles_path, ledger_path, *(path for path, _ in pages)],
        protected,
    )
