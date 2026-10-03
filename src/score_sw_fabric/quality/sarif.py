"""Bounded SARIF 2.1.0 indexing with local frozen-path resolution and native preservation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from score_sw_fabric.assurance.models import bounded_list, nonempty
from score_sw_fabric.process_source.reader import InputError
from score_sw_fabric.quality.import_models import bounded_tree, choice
from score_sw_fabric.quality.models import digest
from score_sw_fabric.runtime.request import parse_json


def object_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("NATIVE_OUTPUT_INVALID", "Native object expected")
    return value


def index_value(value: Any, items: list[Any]) -> int:
    if type(value) is not int or not 0 <= value < len(items):
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Native index is outside collection")
    return value


class Locations:
    def __init__(
        self,
        run: dict[str, Any],
        root: Path,
        files: dict[str, bytes],
        *,
        source_root_base: str | None = None,
    ) -> None:
        self.run, self.root, self.files = run, root, files
        self.artifacts = bounded_list(run.get("artifacts", []), 10000, "/sarif/artifacts")
        self.logical = bounded_list(
            run.get("logicalLocations", []), 10000, "/sarif/logicalLocations"
        )
        self.bases = dict(object_value(run.get("originalUriBaseIds", {})))
        if source_root_base is not None:
            # Explicit consumer context takes precedence (SARIF §3.4.4).
            self.bases[source_root_base] = {"uri": root.as_uri() + "/"}
        if len(self.bases) > 32:
            raise InputError("LIMIT_EXCEEDED", "Too many URI bases")
        self.column_kind = choice(
            run.get("columnKind", "utf16CodeUnits"),
            {"utf16CodeUnits", "unicodeCodePoints"},
            "/columnKind",
        )

    def uri(self, value: Any, ancestors: tuple[str, ...] = ()) -> str:
        item = object_value(value)
        uri = item.get("uri", "")
        if not isinstance(uri, str) or len(uri) > 4096:
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "Malformed native URI")
        try:
            decoded = unquote(uri, encoding="utf-8", errors="strict")
            parsed = urlsplit(decoded)
        except (UnicodeError, ValueError) as exc:
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "Invalid URI encoding") from exc
        if (
            parsed.scheme not in {"", "file"}
            or parsed.netloc not in {"", "localhost"}
            or parsed.query
            or parsed.fragment
            or "\\" in decoded
            or "\x00" in decoded
            or any(p in {".", ".."} for p in parsed.path.split("/"))
        ):
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "External or unsafe native URI")
        if parsed.netloc and parsed.scheme != "file":
            raise InputError(
                "NATIVE_LOCATION_UNRESOLVED", "URI authority requires local file scheme"
            )
        base_id = item.get("uriBaseId")
        if base_id is not None:
            if (
                not isinstance(base_id, str)
                or base_id not in self.bases
                or base_id in ancestors
                or len(ancestors) >= 32
            ):
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Missing or cyclic URI base")
            base = self.uri(self.bases[base_id], (*ancestors, base_id))
            decoded = urljoin(base, decoded)
        return decoded

    def artifact(self, value: Any, seen: tuple[int, ...] = ()) -> str:
        item = object_value(value)
        resolved: str | None = None
        if "index" in item:
            index = index_value(item["index"], self.artifacts)
            if index in seen or len(seen) >= 32:
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Cyclic artifact index")
            descriptor = object_value(self.artifacts[index])
            location = object_value(descriptor.get("location"))
            if "index" in location:
                # SARIF 2.1.0 §3.4.5 permits a descriptor's own array index.
                if index_value(location["index"], self.artifacts) != index:
                    raise InputError(
                        "NATIVE_REFERENCE_UNRESOLVED", "Descriptor index differs from its row"
                    )
                location = {key: value for key, value in location.items() if key != "index"}
            resolved = self.artifact(location, (*seen, index))
            hashes = object_value(descriptor.get("hashes", {}))
            if "sha-256" in hashes and hashes["sha-256"] != digest(self.files[resolved]):
                raise InputError("BASELINE_DRIFT", "Embedded artifact source hash differs")
            contents = descriptor.get("contents")
            if contents is not None:
                contents = object_value(contents)
                if "text" not in contents or not isinstance(contents["text"], str):
                    raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "Unsupported embedded content")
                if contents["text"].encode("utf-8") != self.files[resolved]:
                    raise InputError("BASELINE_DRIFT", "Embedded source content differs")
        if "uri" in item:
            uri = urlsplit(self.uri(item))
            path = Path(uri.path)
            path = path if path.is_absolute() else self.root / path
            if not path.is_relative_to(self.root):
                raise InputError(
                    "NATIVE_LOCATION_UNRESOLVED", "Native location is outside frozen root"
                )
            relative = str(path.relative_to(self.root))
            if relative not in self.files:
                raise InputError("NATIVE_LOCATION_UNRESOLVED", "Native file is not selected")
            if resolved is not None and relative != resolved:
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "URI and artifact index disagree")
            resolved = relative
        if resolved is None:
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "No resolvable artifact location")
        return resolved

    def region(self, value: Any, name: str) -> dict[str, Any]:
        region = object_value(value)
        allowed = {
            "startLine",
            "endLine",
            "startColumn",
            "endColumn",
            "byteOffset",
            "byteLength",
            "charOffset",
            "charLength",
            "snippet",
            "message",
            "properties",
        }
        if set(region) - allowed:
            raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "Unknown region coordinate")
        data = self.files[name]
        lines = data.splitlines()
        for key in (
            "startLine",
            "endLine",
            "startColumn",
            "endColumn",
            "byteOffset",
            "byteLength",
            "charOffset",
            "charLength",
        ):
            if key in region and (
                type(region[key]) is not int
                or region[key] < (1 if key.endswith(("Line", "Column")) else 0)
            ):
                raise InputError("NATIVE_LOCATION_UNRESOLVED", "Invalid native region coordinate")
        for key in ("startLine", "endLine"):
            if key in region and region[key] > len(lines):
                raise InputError("NATIVE_LOCATION_UNRESOLVED", "Region exceeds frozen source lines")
        for prefix in ("start", "end"):
            line, column = region.get(prefix + "Line"), region.get(prefix + "Column")
            if prefix == "end" and line is None:
                line = region.get("startLine")  # SARIF 2.1.0 §3.30.7.
            if column is not None:
                if line is None:
                    raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "Column without its line")
                text = lines[line - 1].decode("utf-8", "replace")
                width = (
                    len(text.encode("utf-16-le")) // 2
                    if self.column_kind == "utf16CodeUnits"
                    else len(text)
                )
                if column > width + 1:
                    raise InputError(
                        "NATIVE_LOCATION_UNRESOLVED", "Column exceeds frozen source line"
                    )
        if region.get("endLine", region.get("startLine", 1)) < region.get("startLine", 1):
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "Reversed native region")
        if (
            region.get("endLine", region.get("startLine")) == region.get("startLine")
            and "endColumn" in region
            and region["endColumn"] < region.get("startColumn", 1)
        ):
            raise InputError("NATIVE_LOCATION_UNRESOLVED", "Reversed native columns")
        character_count = len(data.decode("utf-8", "replace").encode("utf-16-le")) // 2
        for prefix, length in (("byte", len(data)), ("char", character_count)):
            if region.get(prefix + "Offset", 0) + region.get(prefix + "Length", 0) > length:
                raise InputError("NATIVE_LOCATION_UNRESOLVED", "Region exceeds frozen source bytes")
        return region

    def logical_location(self, value: Any, seen: tuple[int, ...] = ()) -> dict[str, Any]:
        item = object_value(value)
        resolved = dict(item)
        if "index" in item:
            index = index_value(item["index"], self.logical)
            if index in seen or len(seen) >= 32:
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Cyclic logical location")
            resolved = {**self.logical_location(self.logical[index], (*seen, index)), **item}
            resolved.pop("index", None)
        if "parentIndex" in resolved:
            parent = index_value(resolved["parentIndex"], self.logical)
            if parent in seen or len(seen) >= 32:
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Cyclic logical parent")
            resolved["parent"] = self.logical_location(self.logical[parent], (*seen, parent))
        if not any(
            isinstance(resolved.get(k), str)
            for k in ("name", "fullyQualifiedName", "decoratedName")
        ):
            raise InputError("NATIVE_OUTPUT_INVALID", "Logical location has no resolved name")
        return resolved

    def walk(self, value: Any, trail: str = "", current: str | None = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if isinstance(value, dict):
            if "artifactLocation" in value:
                current = self.artifact(value["artifactLocation"])
                region = self.region(value.get("region", {}), current)
                result.append({"path": current, "region": region, "kind": trail})
            if "logicalLocations" in value:
                for index, logical in enumerate(
                    bounded_list(value["logicalLocations"], 1000, trail)
                ):
                    result.append(
                        {
                            "path": None,
                            "logical": self.logical_location(logical),
                            "kind": f"{trail}/logicalLocations/{index}",
                        }
                    )
            if "deletedRegion" in value:
                if current is None:
                    raise InputError("NATIVE_LOCATION_UNRESOLVED", "Fix region has no artifact")
                self.region(value["deletedRegion"], current)
            for key, child in value.items():
                if key not in {"artifactLocation", "logicalLocations", "properties"}:
                    result.extend(self.walk(child, trail + "/" + key, current))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                result.extend(self.walk(child, trail + "/" + str(index), current))
        if len(result) > 1000:
            raise InputError("LIMIT_EXCEEDED", "Too many native result locations")
        return result


def rule_reference(
    result: dict[str, Any], tool: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    driver = object_value(tool.get("driver"))
    extensions = bounded_list(tool.get("extensions", []), 32, "/extensions")
    reference = object_value(result.get("rule", {}))
    component = driver
    if reference.get("toolComponent") is not None:
        comp_ref = object_value(reference["toolComponent"])
        if "index" in comp_ref:
            component = object_value(extensions[index_value(comp_ref["index"], extensions)])
        elif "name" in comp_ref:
            candidates = [c for c in [driver, *extensions] if c.get("name") == comp_ref["name"]]
            if len(candidates) != 1:
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Unresolved rule component")
            component = object_value(candidates[0])
        else:
            raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Rule component lacks selection")
        for key in ("name", "guid"):
            if key in comp_ref and comp_ref[key] != component.get(key):
                raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Rule component identity differs")
    rules = bounded_list(component.get("rules", []), 10000, "/rules")
    identifier = reference.get("id", result.get("ruleId"))
    index = reference.get("index", result.get("ruleIndex"))
    if "ruleId" in result and "id" in reference and result["ruleId"] != reference["id"]:
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Rule IDs disagree")
    if "ruleIndex" in result and "index" in reference and result["ruleIndex"] != reference["index"]:
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Rule indexes disagree")
    if index is not None:
        descriptor = object_value(rules[index_value(index, rules)])
        if identifier is not None and identifier != descriptor.get("id"):
            raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Rule ID and descriptor disagree")
    elif identifier is not None:
        candidates = [object_value(r) for r in rules if object_value(r).get("id") == identifier]
        if len(candidates) > 1:
            raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Ambiguous native rule ID")
        descriptor = candidates[0] if candidates else {"id": identifier}
    else:
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Missing native rule identity")
    nonempty(descriptor.get("id"), "/rule/id", max_length=1024)
    return descriptor, component


def message_value(
    result: dict[str, Any], rule: dict[str, Any], component: dict[str, Any]
) -> dict[str, Any]:
    message = object_value(result.get("message"))
    args = bounded_list(message.get("arguments", []), 1000, "/message/arguments")
    if any(not isinstance(a, str) for a in args):
        raise InputError("NATIVE_OUTPUT_INVALID", "Native message arguments must be strings")
    if "text" in message or "markdown" in message:
        for key in ("text", "markdown"):
            if key in message and not isinstance(message[key], str):
                raise InputError("NATIVE_OUTPUT_INVALID", "Native message text must be a string")
        return message
    message_id = message.get("id")
    if not isinstance(message_id, str):
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Native message has no content")
    templates = {
        **object_value(component.get("globalMessageStrings", {})),
        **object_value(rule.get("messageStrings", {})),
    }
    template = object_value(templates.get(message_id))
    if not any(isinstance(template.get(k), str) for k in ("text", "markdown")):
        raise InputError("NATIVE_REFERENCE_UNRESOLVED", "Native message ID cannot be resolved")
    return {**message, "resolved_template": template}


def parse_report(
    data: bytes,
    artifact_id: str,
    root: Path,
    files: dict[str, bytes],
    identity: dict[str, Any],
    *,
    source_root_base: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        document = object_value(parse_json(data, "/sarif"))
    except (RecursionError, ValueError) as exc:
        raise InputError("LIMIT_EXCEEDED", "Native SARIF nesting exceeded") from exc
    bounded_tree(document)
    if document.get("version") != "2.1.0":
        raise InputError("NATIVE_OUTPUT_INVALID", "Unsupported SARIF version")
    if document.get("inlineExternalProperties"):
        raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "External SARIF properties are unsupported")
    runs = bounded_list(document.get("runs"), 32, "/runs")
    findings: list[dict[str, Any]] = []
    gaps = [] if runs else ["SARIF_RUNS_EMPTY"]
    for run_index, value in enumerate(runs):
        run = object_value(value)
        if run.get("externalPropertyFileReferences"):
            raise InputError("NATIVE_OUTPUT_UNSUPPORTED", "External property files are unsupported")
        tool = object_value(run.get("tool"))
        driver = object_value(tool.get("driver"))
        if (
            driver.get("name") != identity["name"]
            or driver.get("semanticVersion", driver.get("version")) != identity["version"]
        ):
            raise InputError(
                "TOOL_IDENTITY_MISMATCH", "Native driver differs from declared identity"
            )
        declared = [*identity["libraries"]]
        if identity["query_pack"] is not None:
            declared.append(identity["query_pack"])
        extensions = bounded_list(tool.get("extensions", []), 32, "/extensions")
        observed = {}
        for ext in extensions:
            ext = object_value(ext)
            name = nonempty(ext.get("name"), "/extension/name", max_length=1024)
            if name in observed:
                raise InputError("TOOL_IDENTITY_MISMATCH", "Duplicate native extension identity")
            observed[name] = ext.get("semanticVersion", ext.get("version"))
        if observed != {p["name"]: p["version"] for p in declared}:
            raise InputError("QUERY_PACK_IDENTITY_MISMATCH", "Native extension selection differs")
        locations = Locations(run, root, files, source_root_base=source_root_base)
        # Validate all indexed descriptor paths, even if no result references them.
        for index in range(len(locations.artifacts)):
            locations.artifact({"index": index})
        for invocation in bounded_list(run.get("invocations", []), 1000, "/invocations"):
            invocation = object_value(invocation)
            if invocation.get("executionSuccessful") is not True:
                gaps.append("PHASE_FAILED")
            for name in ("toolExecutionNotifications", "toolConfigurationNotifications"):
                for notification in bounded_list(invocation.get(name, []), 10000, "/notifications"):
                    notification = object_value(notification)
                    level = choice(
                        notification.get("level", "warning"),
                        {"none", "note", "warning", "error"},
                        "/notification/level",
                    )
                    if level in {"warning", "error"}:
                        gaps.append("SARIF_NOTIFICATION")
                    if notification.get("exception") is not None:
                        gaps.append("QUERY_FAILED")
        if "results" not in run:
            gaps.append("SARIF_RESULTS_MISSING")
        for result_index, value in enumerate(
            bounded_list(run.get("results", []), 10000, "/results")
        ):
            result = object_value(value)
            rule, component = rule_reference(result, tool)
            message = message_value(result, rule, component)
            configuration = object_value(rule.get("defaultConfiguration", {}))
            level = choice(
                result.get("level", configuration.get("level", "warning")),
                {"none", "note", "warning", "error"},
                "/result/level",
            )
            suppressions = bounded_list(result.get("suppressions", []), 1000, "/suppressions")
            for suppression in suppressions:
                suppression = object_value(suppression)
                choice(suppression.get("kind"), {"inSource", "external"}, "/suppression/kind")
                if "status" in suppression:
                    choice(
                        suppression["status"],
                        {"accepted", "underReview", "rejected"},
                        "/suppression/status",
                    )
            fingerprints = {}
            for name in ("fingerprints", "partialFingerprints"):
                values = object_value(result.get(name, {}))
                if any(not isinstance(v, str) for v in values.values()):
                    raise InputError("NATIVE_OUTPUT_INVALID", "Fingerprint must be a string")
                fingerprints[name] = values
            findings.append(
                {
                    "native_id": rule["id"],
                    "native_level": level,
                    "artifact_id": artifact_id,
                    "run_index": run_index,
                    "result_index": result_index,
                    "message": message,
                    "locations": locations.walk(result),
                    "fingerprints": fingerprints,
                    "suppressions": suppressions,
                    "native_record": result,
                    "native_rule": rule,
                    "rule_component": {
                        k: component[k]
                        for k in ("name", "version", "semanticVersion", "guid")
                        if k in component
                    },
                    "native_kind": choice(
                        result.get("kind", "fail"),
                        {"notApplicable", "pass", "fail", "review", "open", "informational"},
                        "/result/kind",
                    ),
                }
            )
            if len(findings) > 10000:
                raise InputError("LIMIT_EXCEEDED", "Too many aggregate SARIF results")
    return findings, sorted(set(gaps))
