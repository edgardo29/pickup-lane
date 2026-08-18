from __future__ import annotations

import ast
import copy
import json
from functools import lru_cache, partial
from inspect import isfunction, ismethod
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = Path(__file__).with_name("authorization_matrix.json")
REQUIREMENTS_PATH = REPO_ROOT / "backend/tests/support/requirements/ws03_04a.json"

AUTH_PREFIX = "backend.services.auth_service:"
EXCLUDED_METHODS = {"HEAD", "OPTIONS"}
EXPECTED_INTAKE_PATH = "docs/production-readiness/planning/passes/ws03/ws03-04-intake.md"
EXPECTED_PLAN_PATH = (
    "docs/production-readiness/planning/passes/ws03/"
    "ws03-04a-authorization-matrix-foundation.md"
)
EXPECTED_BASELINE_SHA = "22855d0d0b8e67be733de1fea6e3771f0587cfa9"
EXPECTED_INTAKE_SHA = (
    "e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4"
)
EXPECTED_GRAPH = "WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D"
EXPECTED_ROUTE_COUNT = 289
LEGACY_TEST_PATH = "backend/tests/" + "legacy/"

REQUIRED_ROUTE_FIELDS = {
    "method",
    "path",
    "name",
    "tags",
    "source_module",
    "auth_dependencies",
    "route_disposition",
    "disposition_reason",
    "child_owner",
    "owner_reason",
    "behavior_owner_detail",
    "actor_classes",
    "resource_family",
    "resource_id_fields",
    "relationship_rules",
    "workflow_state_rules",
    "list_query_rules",
    "field_rules",
    "function_rules",
    "role_rules",
    "concealment_policy",
    "negative_proof_owner",
    "negative_proof_owner_detail",
    "negative_proof_reason",
    "source_ids",
    "gap_refs",
}
REQUIRED_FAMILY_FIELDS = {
    "family_id",
    "summary",
    "primary_child_owner",
    "owner_reason",
    "behavior_owner_detail",
    "source_ids",
    "gap_refs",
    "routes",
}
REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "source_type",
    "path",
    "title",
    "authority_role",
    "evidence_classification",
    "description",
}
REQUIRED_GAP_FIELDS = {
    "gap_id",
    "state",
    "title",
    "reason",
    "owner",
    "owner_type",
    "source_ids",
    "requirement_ids",
    "affected_families",
    "affected_routes",
    "resolution_condition",
    "blocks_ws03_04a_acceptance",
}

VALID_OWNERS = {
    "WS03-04B",
    "WS03-04C",
    "WS03-04D",
    "covered_elsewhere",
    "not_applicable",
    "blocked",
}
VALID_CHILDREN = {"WS03-04B", "WS03-04C", "WS03-04D"}
VALID_DISPOSITIONS = {
    "protected",
    "public",
    "optional_auth",
    "provider_callback",
    "health_or_root",
    "retired_or_tombstone",
    "excluded_non_api",
}
VALID_CONCEALMENT = {
    "401",
    "403",
    "404",
    "410",
    "mixed",
    "not_applicable",
    "blocked_owner_decision",
}
VALID_SOURCE_TYPES = {
    "durable_doc",
    "workflow",
    "template",
    "execution_register",
    "frozen_intake",
    "blueprint",
    "remediation_plan",
    "decision_record",
    "accepted_predecessor_plan",
    "repository_source",
    "repository_test_standard",
    "current_route_table",
}
VALID_AUTHORITY_ROLES = {
    "authority",
    "frozen_boundary",
    "accepted_repository_evidence",
    "repository_truth",
    "standard",
    "derived_current_truth",
}
VALID_EVIDENCE_CLASSES = {
    "durable_authority",
    "repository_truth",
    "accepted_repository_source_test_evidence",
    "governance_boundary",
    "derived_inventory",
}
VALID_GAP_STATES = {
    "owned_by_later_child",
    "covered_elsewhere",
    "deferred_external",
    "blocked_owner_decision",
}
VALID_GAP_OWNER_TYPES = {
    "child_pass",
    "later_pass",
    "external_evidence",
    "governance_owner",
    "covered_elsewhere",
}
REQUIREMENT_IDS = {f"WS03-04A-R{number}" for number in range(1, 10)}
REQUIRED_REQUIREMENT_IDS = {f"WS03-04A-R{number}" for number in range(1, 9)}
DEFERRED_REQUIREMENT_ID = "WS03-04A-R9"


@lru_cache(maxsize=1)
def _matrix() -> dict[str, Any]:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _requirement_declarations() -> dict[str, dict[str, Any]]:
    with REQUIREMENTS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema_version"] == 1
    return {entry["id"]: entry for entry in payload["requirements"]}


def _callable_identity(callable_obj: Any) -> str:
    if isinstance(callable_obj, partial):
        raise AssertionError(f"Unrepresentable partial dependency: {callable_obj!r}")
    if not (isfunction(callable_obj) or ismethod(callable_obj)):
        raise AssertionError(f"Unrepresentable callable dependency: {callable_obj!r}")

    module = getattr(callable_obj, "__module__", None)
    qualname = getattr(callable_obj, "__qualname__", None)
    if not module or not qualname or "<locals>" in qualname or qualname == "<lambda>":
        raise AssertionError(f"Unstable dependency identity: {callable_obj!r}")

    identity = f"{module}:{qualname}"
    wrapped_seen: set[int] = set()
    wrapped_parts: list[str] = []
    wrapped = getattr(callable_obj, "__wrapped__", None)
    while wrapped is not None:
        if id(wrapped) in wrapped_seen:
            raise AssertionError(f"Wrapper cycle in dependency identity: {callable_obj!r}")
        wrapped_seen.add(id(wrapped))
        wrapped_module = getattr(wrapped, "__module__", None)
        wrapped_qualname = getattr(wrapped, "__qualname__", None)
        if not wrapped_module or not wrapped_qualname or "<locals>" in wrapped_qualname:
            raise AssertionError(f"Unstable wrapped dependency identity: {wrapped!r}")
        wrapped_parts.append(f"{wrapped_module}:{wrapped_qualname}")
        wrapped = getattr(wrapped, "__wrapped__", None)

    if wrapped_parts:
        return f"{identity}[wrapped={'|'.join(wrapped_parts)}]"
    return identity


def _walk_dependency_calls(dependant: Any) -> list[Any]:
    calls: list[Any] = []
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            calls.append(dependency.call)
        calls.extend(_walk_dependency_calls(dependency))
    return calls


def _auth_dependencies(route: APIRoute) -> list[str]:
    identities: dict[str, int] = {}
    for call in _walk_dependency_calls(route.dependant):
        identity = _callable_identity(call)
        if identity.startswith(AUTH_PREFIX):
            previous_id = identities.setdefault(identity, id(call))
            assert previous_id == id(call), f"auth dependency identity collision: {identity}"
    return sorted(identities)


@lru_cache(maxsize=1)
def _current_apiroute_count() -> int:
    from backend.main import app

    return sum(1 for route in app.routes if isinstance(route, APIRoute))


@lru_cache(maxsize=1)
def _current_route_map() -> dict[tuple[str, str], APIRoute]:
    from backend.main import app

    routes: dict[tuple[str, str], APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods - EXCLUDED_METHODS):
            key = (method, route.path_format)
            assert key not in routes, f"duplicate current route key: {key}"
            routes[key] = route
    return routes


def _flatten_matrix_routes(
    matrix: dict[str, Any] | None = None,
) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    matrix = matrix or _matrix()
    routes: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for family in matrix["route_families"]:
        for route in family["routes"]:
            key = (route["method"], route["path"])
            assert key not in routes, f"duplicate matrix route key: {key}"
            routes[key] = (family, route)
    return routes


def _assert_route_key_sets_match(matrix: dict[str, Any]) -> None:
    matrix_keys = set(_flatten_matrix_routes(matrix))
    current_keys = set(_current_route_map())
    missing = sorted(current_keys - matrix_keys)
    stale = sorted(matrix_keys - current_keys)
    assert not missing, f"missing current routes from authorization matrix: {missing}"
    assert not stale, f"stale authorization matrix routes no longer registered: {stale}"


def _all_route_entries(matrix: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [route for _, route in _flatten_matrix_routes(matrix).values()]


def _collect_requirement_marker_ids() -> set[str]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    marker_ids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "requirement":
            continue
        value = node.func.value
        if not (
            isinstance(value, ast.Attribute)
            and value.attr == "mark"
            and isinstance(value.value, ast.Name)
            and value.value.id == "pytest"
        ):
            continue
        marker_ids.update(
            arg.value for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        )
    return marker_ids


@pytest.mark.requirement("WS03-04A-R1", "WS03-04A-R6")
def test_authorization_matrix_includes_every_registered_route_key() -> None:
    matrix = _matrix()
    current_apiroute_count = _current_apiroute_count()
    current_routes = _current_route_map()

    assert matrix["baseline_apiroute_count"] == current_apiroute_count
    assert matrix["baseline_flattened_route_key_count"] == len(current_routes)
    assert current_apiroute_count == EXPECTED_ROUTE_COUNT
    assert len(current_routes) == EXPECTED_ROUTE_COUNT
    _assert_route_key_sets_match(matrix)


@pytest.mark.requirement("WS03-04A-R2", "WS03-04A-R5")
def test_authorization_matrix_schema_requires_authz_dimensions() -> None:
    matrix = _matrix()

    assert matrix["schema_version"] == 1
    assert matrix["pass_id"] == "WS03-04A"
    assert matrix["parent_pass"] == "WS03-04"
    assert matrix["accepted_baseline_sha"] == EXPECTED_BASELINE_SHA
    assert matrix["frozen_intake"] == {
        "path": EXPECTED_INTAKE_PATH,
        "sha256": EXPECTED_INTAKE_SHA,
    }
    assert matrix["child_dependency_graph"] == EXPECTED_GRAPH
    assert matrix["route_key_format"] == "METHOD path_format"
    assert matrix["excluded_methods"] == ["HEAD", "OPTIONS"]
    assert matrix["auth_dependency_serialization"] == {
        "version": 1,
        "route_tree": "APIRoute.dependant.dependencies recursive traversal",
        "identity_format": "module:qualname",
        "recorded_value": "sorted unique backend.services.auth_service dependency identities",
    }

    assert matrix["route_families"], "matrix must contain explicit route families"
    assert matrix["sources"], "matrix must contain source traceability"
    for family in matrix["route_families"]:
        assert REQUIRED_FAMILY_FIELDS <= family.keys()
        assert "gap_state" not in family
        assert "gap_reason" not in family
        assert family["family_id"]
        assert family["summary"]
        assert family["owner_reason"]
        assert isinstance(family["routes"], list) and family["routes"]
        assert isinstance(family["source_ids"], list) and family["source_ids"]
        assert isinstance(family["gap_refs"], list)

    for route in _all_route_entries(matrix):
        assert REQUIRED_ROUTE_FIELDS <= route.keys()
        assert "gap_state" not in route
        assert "gap_reason" not in route
        assert route["method"] not in EXCLUDED_METHODS
        assert route["path"].startswith("/")
        assert isinstance(route["tags"], list)
        assert isinstance(route["auth_dependencies"], list)
        assert route["disposition_reason"]
        assert route["owner_reason"]
        assert isinstance(route["actor_classes"], list) and route["actor_classes"]
        assert isinstance(route["resource_id_fields"], list)
        assert route["relationship_rules"]
        assert route["workflow_state_rules"]
        assert route["list_query_rules"]
        assert route["field_rules"]
        assert route["function_rules"]
        assert route["role_rules"]
        assert route["concealment_policy"] in VALID_CONCEALMENT
        assert route["negative_proof_owner_detail"]
        assert route["negative_proof_reason"]
        assert isinstance(route["source_ids"], list) and route["source_ids"]
        assert isinstance(route["gap_refs"], list)


@pytest.mark.requirement("WS03-04A-R7", "WS03-04A-R8")
def test_authorization_matrix_source_and_gap_references_are_canonical() -> None:
    matrix = _matrix()
    sources = matrix["sources"]
    source_ids = [source["source_id"] for source in sources]
    source_id_set = set(source_ids)
    assert len(source_ids) == len(source_id_set)

    for source in sources:
        assert REQUIRED_SOURCE_FIELDS <= source.keys()
        assert source["source_type"] in VALID_SOURCE_TYPES
        assert source["authority_role"] in VALID_AUTHORITY_ROLES
        assert source["evidence_classification"] in VALID_EVIDENCE_CLASSES
        assert LEGACY_TEST_PATH not in source["path"]
        if source["source_type"] != "current_route_table":
            assert (REPO_ROOT / source["path"]).exists(), source
        if source["source_type"] == "accepted_predecessor_plan" or source["path"].startswith(
            "backend/tests/workflows/"
        ) or source["path"].startswith("backend/tests/support/requirements/ws03_0"):
            assert source["authority_role"] == "accepted_repository_evidence"
            assert source["evidence_classification"] == "accepted_repository_source_test_evidence"

    family_by_id = {family["family_id"]: family for family in matrix["route_families"]}
    assert len(family_by_id) == len(matrix["route_families"])
    route_by_key = {key: route for key, (_, route) in _flatten_matrix_routes(matrix).items()}
    gap_by_id = {gap["gap_id"]: gap for gap in matrix["uncovered_gaps"]}
    assert len(gap_by_id) == len(matrix["uncovered_gaps"])

    referenced_sources: set[str] = set()
    referenced_gaps: set[str] = set()
    for family in matrix["route_families"]:
        referenced_sources.update(family["source_ids"])
        referenced_gaps.update(family["gap_refs"])
    for route in route_by_key.values():
        referenced_sources.update(route["source_ids"])
        referenced_gaps.update(route["gap_refs"])
    for gap in matrix["uncovered_gaps"]:
        assert REQUIRED_GAP_FIELDS <= gap.keys()
        assert gap["state"] in VALID_GAP_STATES
        assert gap["owner_type"] in VALID_GAP_OWNER_TYPES
        assert gap["reason"]
        assert gap["owner"] and gap["owner"] != gap["owner_type"]
        assert isinstance(gap["blocks_ws03_04a_acceptance"], bool)
        assert set(gap["source_ids"]) <= source_id_set
        assert set(gap["requirement_ids"]) <= REQUIREMENT_IDS
        assert set(gap["affected_families"]) <= set(family_by_id)
        referenced_sources.update(gap["source_ids"])
        assert (
            gap["affected_families"]
            or gap["affected_routes"]
            or gap["requirement_ids"]
        ), f"orphaned gap: {gap['gap_id']}"
        if gap["state"] == "blocked_owner_decision":
            assert gap["blocks_ws03_04a_acceptance"] is True
        else:
            assert gap["blocks_ws03_04a_acceptance"] is False
        for family_id in gap["affected_families"]:
            assert gap["gap_id"] in family_by_id[family_id]["gap_refs"]
        for route_ref in gap["affected_routes"]:
            key = (route_ref["method"], route_ref["path"])
            assert key in route_by_key
            assert gap["gap_id"] in route_by_key[key]["gap_refs"]

    assert referenced_sources <= source_id_set
    assert referenced_gaps <= set(gap_by_id)
    for family in matrix["route_families"]:
        for gap_id in family["gap_refs"]:
            assert family["family_id"] in gap_by_id[gap_id]["affected_families"]
    for key, route in route_by_key.items():
        for gap_id in route["gap_refs"]:
            gap_routes = {
                (route_ref["method"], route_ref["path"])
                for route_ref in gap_by_id[gap_id]["affected_routes"]
            }
            assert key in gap_routes


@pytest.mark.requirement("WS03-04A-R3")
def test_route_and_family_ownership_is_homogeneous_and_complete() -> None:
    matrix = _matrix()

    for family in matrix["route_families"]:
        assert family["primary_child_owner"] in VALID_OWNERS
        assert family["primary_child_owner"] != "WS03-04A"
        assert family["behavior_owner_detail"]
        if family["primary_child_owner"] in VALID_CHILDREN:
            assert family["behavior_owner_detail"] == family["primary_child_owner"]
        if family["primary_child_owner"] == "covered_elsewhere":
            assert family["behavior_owner_detail"] not in VALID_OWNERS
        if family["primary_child_owner"] == "blocked":
            assert "blocked_owner_decision" in {
                _matrix_gap["state"]
                for _matrix_gap in matrix["uncovered_gaps"]
                if _matrix_gap["gap_id"] in family["gap_refs"]
            }
        family_route_owners = {route["child_owner"] for route in family["routes"]}
        assert family_route_owners == {family["primary_child_owner"]}
        family_owner_details = {route["behavior_owner_detail"] for route in family["routes"]}
        assert family_owner_details == {family["behavior_owner_detail"]}

    route_owners = {route["child_owner"] for route in _all_route_entries(matrix)}
    assert VALID_CHILDREN <= route_owners
    assert "covered_elsewhere" in route_owners
    assert "not_applicable" in route_owners
    assert "WS03-04A" not in route_owners
    assert "blocked" not in route_owners


@pytest.mark.requirement("WS03-04A-R3", "WS03-04A-R5")
def test_negative_proof_owner_matches_behavioral_owner_or_records_exception() -> None:
    matrix = _matrix()
    gap_by_id = {gap["gap_id"]: gap for gap in matrix["uncovered_gaps"]}

    for route in _all_route_entries(matrix):
        assert route["negative_proof_owner"] in VALID_OWNERS
        assert route["negative_proof_owner"] != "WS03-04A"
        if route["child_owner"] in VALID_CHILDREN:
            assert route["negative_proof_owner"] == route["child_owner"]
            assert route["negative_proof_owner_detail"] == route["child_owner"]
        elif route["child_owner"] == "covered_elsewhere":
            assert route["negative_proof_owner"] == "covered_elsewhere"
            assert route["negative_proof_owner_detail"] not in VALID_OWNERS
            if route["gap_refs"]:
                assert any(gap_by_id[gap_id]["owner"] == route["negative_proof_owner_detail"] for gap_id in route["gap_refs"])
        elif route["child_owner"] == "not_applicable":
            assert route["negative_proof_owner"] == "not_applicable"
            assert route["negative_proof_owner_detail"] == "not_applicable"
        elif route["child_owner"] == "blocked":
            assert route["negative_proof_owner"] == "blocked"
            assert route["gap_refs"]


@pytest.mark.requirement("WS03-04A-R4", "WS03-04A-R6")
def test_route_dispositions_match_backend_auth_dependencies() -> None:
    for route in _all_route_entries():
        assert route["route_disposition"] in VALID_DISPOSITIONS
        assert route["disposition_reason"].strip()
        if route["route_disposition"] == "protected":
            assert route["auth_dependencies"], route
            assert all(dep.startswith(AUTH_PREFIX) for dep in route["auth_dependencies"])
        elif route["route_disposition"] == "optional_auth":
            assert "backend.services.auth_service:get_optional_current_app_user" in route["auth_dependencies"]
        elif route["route_disposition"] == "provider_callback":
            assert route["path"] == "/stripe/webhook"
            assert route["child_owner"] == "covered_elsewhere"
            assert route["behavior_owner_detail"] == "WS05"
        elif route["route_disposition"] == "health_or_root":
            assert route["path"] in {"/", "/live", "/ready", "/db-health"}
            assert not route["auth_dependencies"]
        elif route["route_disposition"] == "public":
            assert not route["auth_dependencies"]
        elif route["route_disposition"] == "retired_or_tombstone":
            assert route["concealment_policy"] == "410"


@pytest.mark.requirement("WS03-04A-R6", "WS03-04A-R8")
def test_recorded_authorization_dependencies_match_current_fastapi_dependency_tree() -> None:
    current_routes = _current_route_map()
    matrix_routes = _flatten_matrix_routes()

    for key, current_route in current_routes.items():
        _, matrix_route = matrix_routes[key]
        assert matrix_route["auth_dependencies"] == _auth_dependencies(current_route), key


@pytest.mark.requirement("WS03-04A-R3", "WS03-04A-R6")
def test_child_owner_partition_has_no_gap_or_overlap() -> None:
    matrix_routes = _flatten_matrix_routes()
    assert len(matrix_routes) == EXPECTED_ROUTE_COUNT

    owners_by_key: dict[tuple[str, str], set[str]] = {}
    for key, (_, route) in matrix_routes.items():
        owners_by_key.setdefault(key, set()).add(route["child_owner"])

    assert all(len(owners) == 1 for owners in owners_by_key.values())
    assert set(owners_by_key) == set(_current_route_map())
    assert _matrix()["child_dependency_graph"] == EXPECTED_GRAPH


@pytest.mark.requirement("WS03-04A-R1", "WS03-04A-R6", "WS03-04A-R8")
def test_route_drift_validator_fails_for_missing_stale_or_duplicate_routes() -> None:
    matrix = copy.deepcopy(_matrix())
    first_family = matrix["route_families"][0]
    first_route = first_family["routes"][0]

    missing_route_matrix = copy.deepcopy(matrix)
    missing_route_matrix["route_families"][0]["routes"] = first_family["routes"][1:]
    with pytest.raises(AssertionError, match="missing current routes"):
        _assert_route_key_sets_match(missing_route_matrix)

    stale_route_matrix = copy.deepcopy(matrix)
    stale_route_matrix["route_families"][0]["routes"][0] = {
        **first_route,
        "method": "GET",
        "path": "/ws03-04a-stale-route",
    }
    with pytest.raises(AssertionError, match="missing current routes"):
        _assert_route_key_sets_match(stale_route_matrix)
    with pytest.raises(AssertionError, match="stale authorization matrix routes"):
        stale_only_matrix = copy.deepcopy(matrix)
        stale_only_matrix["route_families"].append(
            {
                **first_family,
                "family_id": "stale_route_probe",
                "routes": [{**first_route, "path": "/ws03-04a-stale-route"}],
            }
        )
        _assert_route_key_sets_match(stale_only_matrix)

    duplicate_route_matrix = copy.deepcopy(matrix)
    duplicate_route_matrix["route_families"][0]["routes"].append(copy.deepcopy(first_route))
    with pytest.raises(AssertionError, match="duplicate matrix route key"):
        _flatten_matrix_routes(duplicate_route_matrix)


@pytest.mark.requirement("WS03-04A-R7", "WS03-04A-R8")
def test_negative_space_blocks_frontend_legacy_provider_and_deferred_false_closure() -> None:
    matrix = _matrix()
    sources = matrix["sources"]

    assert all(LEGACY_TEST_PATH not in json.dumps(source) for source in sources)
    assert all(not source["path"].startswith("frontend/") for source in sources)
    assert EXPECTED_PLAN_PATH in {source["path"] for source in sources}

    for source in sources:
        if source["path"].startswith("backend/tests/workflows/") or source["path"].startswith(
            "backend/tests/support/requirements/ws03_0"
        ):
            assert source["evidence_classification"] == "accepted_repository_source_test_evidence"

    stripe_routes = [
        route for route in _all_route_entries(matrix) if route["path"] == "/stripe/webhook"
    ]
    assert len(stripe_routes) == 1
    assert stripe_routes[0]["child_owner"] == "covered_elsewhere"
    assert stripe_routes[0]["behavior_owner_detail"] == "WS05"
    assert "WS03-04A-G001" in stripe_routes[0]["gap_refs"]

    assert DEFERRED_REQUIREMENT_ID not in _collect_requirement_marker_ids()


@pytest.mark.requirement("WS03-04A-R7")
def test_requirement_declaration_and_markers_match_ws03_04a_scope() -> None:
    declarations = _requirement_declarations()
    assert set(declarations) == REQUIREMENT_IDS

    for requirement_id in REQUIRED_REQUIREMENT_IDS:
        declaration = declarations[requirement_id]
        assert declaration["owning_pass"] == "WS03-04A"
        assert declaration["state"] == "required"
        assert declaration["scope"] == "workflows/authorization_matrix_foundation"
        assert declaration["reason"].strip()

    deferred = declarations[DEFERRED_REQUIREMENT_ID]
    assert deferred["owning_pass"] == "WS03-04A"
    assert deferred["state"] == "deferred"
    assert deferred["scope"] == "governance"
    assert deferred["reason"].strip()

    marker_ids = _collect_requirement_marker_ids()
    assert REQUIRED_REQUIREMENT_IDS <= marker_ids
    assert DEFERRED_REQUIREMENT_ID not in marker_ids
