"""Public typed shapes for catalogue consumers.

Raw and normalized attribute maps intentionally remain open: native exporters may add
non-normative fields. Validation occurs in the importer against pinned schemas.
"""

from typing import Any, Literal, TypedDict


class NativeType(TypedDict):
    name: str
    definition: dict[str, Any]
    source_ref: dict[str, Any]


class NativeEntity(TypedDict):
    source_id: str
    export_version: str
    export_key: str
    native_id: str
    native_version: int
    type: str
    title: str | None
    content: str | None
    status: str | None
    is_external: bool
    is_template: bool
    template_keys: dict[str, str | None]
    source_ref: dict[str, Any]
    raw: dict[str, Any]
    normalized: dict[str, Any]


class Relation(TypedDict):
    source_id: str
    native_id: str
    native_version: int
    field: str
    direction: Literal["forward", "backlink"]
    raw_target: str
    target_id: str
    target_version_selector: int | None
    target_source_id: str
    resolved_native_version: int
    source_ref: dict[str, Any]
    pointer: str


class Catalogue(TypedDict):
    schema_version: int
    manifest: dict[str, Any]
    metamodel_raw: dict[str, Any]
    types: list[NativeType]
    entities: list[NativeEntity]
    relations: list[Relation]
    engineering_readiness: Literal["not_evaluated"]
