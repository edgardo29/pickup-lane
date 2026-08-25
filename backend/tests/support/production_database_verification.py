from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


EVIDENCE_STATES = frozenset(
    {
        "blocked",
        "deferred_to_ws04_01d",
        "not_applicable",
        "stale",
        "unverified",
        "verified",
    }
)

CONTRACT_STATES = frozenset(
    {
        "provider_independent_template",
        "ws04_01d_final_evidence",
    }
)

REQUIRED_METADATA_FIELDS = (
    "provider_or_control_plane",
    "environment",
    "date_collected",
    "reviewer",
    "purpose",
    "supported_controls",
    "supported_passes",
    "source_type",
    "sanitized_evidence_reference",
    "raw_evidence_location_reference",
    "open_gaps",
)

C_TEMPLATE_DEFERRED_METADATA_FIELDS = (
    "provider_or_control_plane",
    "environment",
    "date_collected",
    "reviewer",
    "source_type",
    "sanitized_evidence_reference",
)

FINAL_METADATA_VALUE_FIELDS = (
    "provider_or_control_plane",
    "environment",
    "date_collected",
    "reviewer",
    "purpose",
    "supported_controls",
    "supported_passes",
    "source_type",
    "sanitized_evidence_reference",
)

REQUIRED_FINAL_TOPOLOGY_FIELDS = (
    "provider_capacity_source",
    "connection_mode",
    "api_instance_ceiling",
    "api_processes_per_instance",
    "autoscaling_ceiling_or_disabled_evidence",
    "additional_rolling_overlap",
    "deployed_pool_values",
    "migration_credential_separation",
    "independent_engine_per_process",
    "shutdown_pool_release",
    "startup_connection_behavior",
)

CONDITIONAL_POOLER_TOPOLOGY_FIELDS = (
    "pooler_client_connection_ceiling",
    "pooler_server_connection_ceiling",
)

CONNECTION_MODE_VALUES = frozenset(
    {
        "direct",
        "provider_pooler",
        "proxy",
    }
)

BUDGET_INPUT_FIELDS = (
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "max_api_instances",
    "api_processes_per_instance",
    "additional_rolling_overlap_api_instances",
    "api_processes_per_additional_overlap_instance",
    "background_worker_connections",
    "scheduler_or_job_runner_connections",
    "migration_connections",
    "monitoring_connections",
    "reporting_or_support_connections",
    "routine_human_access_connections",
    "operational_reserve_connections",
    "usable_provider_connection_capacity",
)

NON_API_BUDGET_INPUT_FIELDS = (
    "background_worker_connections",
    "scheduler_or_job_runner_connections",
    "migration_connections",
    "monitoring_connections",
    "reporting_or_support_connections",
    "routine_human_access_connections",
    "operational_reserve_connections",
)

REQUIRED_LIMIT_BASIS_FIELDS = (
    "protected_resource_or_failure_mode",
    "enforcing_layers",
    "accountable_owner",
    "provider_platform_constraints",
    "expected_workload_and_abuse_risk",
    "failure_cost_and_recovery_behavior",
    "configurability",
    "boundary_and_multi_instance_test_evidence",
    "telemetry",
    "rollback_or_safe_adjustment",
    "reassessment_triggers",
)

MUTABLE_CAPACITY_INPUT_FIELDS = (
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "max_api_instances",
    "api_processes_per_instance",
    "additional_rolling_overlap_api_instances",
    "api_processes_per_additional_overlap_instance",
    "autoscaling_ceiling_or_disabled_evidence",
    "pooler_or_proxy_mode",
    "usable_provider_connection_capacity",
)

MUTABLE_CAPACITY_REQUIREMENTS = (
    "accountable_owner",
    "protected_resource_or_failure_mode",
    "enforcing_layers",
    "provider_platform_constraints",
    "expected_workload_and_abuse_risk",
    "failure_cost_and_recovery_behavior",
    "configurability",
    "reassessment_trigger",
    "boundary_and_multi_instance_evidence",
    "safe_adjustment_or_forward_fix",
    "rollback_or_abort_condition",
    "post_change_reverification",
)

RUNTIME_TOPOLOGY_FIELDS = (
    "provider_capacity_source",
    "connection_mode",
    "pooler_client_connection_ceiling",
    "pooler_server_connection_ceiling",
    "api_instance_ceiling",
    "api_processes_per_instance",
    "autoscaling_ceiling_or_disabled_evidence",
    "additional_rolling_overlap",
    "deployed_pool_values",
    "migration_credential_separation",
    "independent_engine_per_process",
    "shutdown_pool_release",
    "startup_connection_behavior",
)

ROLE_CLASSES = (
    "application_runtime",
    "migration_execution",
    "background_worker_or_scheduler",
    "read_only_reporting_or_support",
    "backup_or_restore_database_access",
    "routine_human_access",
    "schema_or_object_owner",
)

ROLE_CHECKS = (
    "superuser",
    "database_ownership",
    "schema_ownership",
    "createdb",
    "createrole",
    "replication",
    "bypassrls",
    "schema_usage_create_privileges",
    "table_privileges",
    "sequence_privileges",
    "function_privileges",
    "default_privileges",
    "search_path",
    "effective_application_role",
    "effective_migration_role",
    "support_reporting_human_access",
)

APPLICATION_RUNTIME_FORBIDDEN_FLAGS = (
    "superuser",
    "database_owner",
    "schema_owner",
    "migration_owner",
    "role_admin",
    "createdb",
    "createrole",
    "replication",
    "bypassrls",
    "broad_provider_admin",
    "routine_ddl_capable",
)

FINAL_ROLE_COMPLETION_CHECKS = (
    "ownership",
    "search_path",
    "default_privileges",
    "role_attributes",
)

FINAL_ROLE_EVIDENCE_CHECKS = tuple(
    sorted(set(ROLE_CHECKS) | set(FINAL_ROLE_COMPLETION_CHECKS))
)

FINAL_ROLE_REQUIRED_PRESENT_CLASSES = (
    "application_runtime",
    "migration_execution",
    "schema_or_object_owner",
)

SENSITIVE_VALUE_PATTERNS = (
    ("database URL", re.compile(r"\bpostgres(?:ql)?(?:\+\w+)?://[^\s\"'<>]+", re.IGNORECASE)),
    ("credential URL", re.compile(r"://[^/\s:@]+:[^@\s/]+@")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("signed URL", re.compile(r"\bX-Amz-(?:Signature|Credential)=", re.IGNORECASE)),
    (
        "private dashboard URL",
        re.compile(
            r"https?://[^\s\"'<>]*(?:dashboard|console|/dashboard|/projects?/|"
            r"/accounts?)[^\s\"'<>]*",
            re.IGNORECASE,
        ),
    ),
    (
        "provider project/account identifier",
        re.compile(
            r"\b(?:project|account)[_-]?(?:id|identifier)?[:= -]+"
            r"[A-Za-z0-9][A-Za-z0-9_-]{5,}"
            r"|\b(?:private-)?(?:project|account)[_-][A-Za-z0-9][A-Za-z0-9_-]{2,}",
            re.IGNORECASE,
        ),
    ),
    (
        "private hostname",
        re.compile(r"\b[A-Za-z0-9.-]+\.(?:internal|local|lan|corp)\b", re.IGNORECASE),
    ),
    (
        "raw evidence reference",
        re.compile(
            r"\braw[-_](?:screenshot|export|log|evidence)\b"
            r"|\b(?:screenshot|export|log)[-_/][^\s\"'<>]+",
            re.IGNORECASE,
        ),
    ),
    (
        "personal email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "payment card number",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    ),
    (
        "secret assignment",
        re.compile(r"\b(?:password|secret|token|api[_-]?key)\b\s*[:=]\s*[^,\s]+", re.IGNORECASE),
    ),
    (
        "IP address",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    ),
)


@dataclass(frozen=True)
class ConnectionBudget:
    per_process_application_connections: int
    api_steady_state_connections: int
    api_incremental_rolling_overlap_connections: int
    total_budgeted_peak_connections: int
    remaining_headroom: int

    def as_dict(self) -> dict[str, int]:
        return {
            "per_process_application_connections": self.per_process_application_connections,
            "api_steady_state_connections": self.api_steady_state_connections,
            "api_incremental_rolling_overlap_connections": self.api_incremental_rolling_overlap_connections,
            "total_budgeted_peak_connections": self.total_budgeted_peak_connections,
            "remaining_headroom": self.remaining_headroom,
        }


def calculate_connection_budget(values: Mapping[str, Any]) -> ConnectionBudget:
    errors = budget_input_errors(values)
    if errors:
        raise ValueError("; ".join(errors))

    typed_values = {field: values[field] for field in BUDGET_INPUT_FIELDS}
    per_process = typed_values["DB_POOL_SIZE"] + typed_values["DB_MAX_OVERFLOW"]
    steady = (
        typed_values["max_api_instances"]
        * typed_values["api_processes_per_instance"]
        * per_process
    )
    overlap = (
        typed_values["additional_rolling_overlap_api_instances"]
        * typed_values["api_processes_per_additional_overlap_instance"]
        * per_process
    )
    non_api_total = sum(typed_values[field] for field in NON_API_BUDGET_INPUT_FIELDS)
    total = steady + overlap + non_api_total
    headroom = typed_values["usable_provider_connection_capacity"] - total

    return ConnectionBudget(
        per_process_application_connections=per_process,
        api_steady_state_connections=steady,
        api_incremental_rolling_overlap_connections=overlap,
        total_budgeted_peak_connections=total,
        remaining_headroom=headroom,
    )


def budget_input_errors(values: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in BUDGET_INPUT_FIELDS:
        if field not in values:
            errors.append(f"missing budget input: {field}")
            continue
        value = values[field]
        if not _is_non_negative_int(value):
            errors.append(f"{field} must be a non-negative integer")
    return errors


def validate_evidence_contract(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    if record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if record.get("owning_pass") != "WS04-01C":
        errors.append("owning_pass must be WS04-01C")
    if record.get("future_population_owner") != "WS04-01D":
        errors.append("future_population_owner must be WS04-01D")
    contract_state = record.get("contract_state")
    if contract_state not in CONTRACT_STATES:
        errors.append(f"contract_state has unsupported value: {contract_state!r}")

    metadata = _mapping(record.get("metadata"), "metadata", errors)
    _validate_stateful_fields(metadata, REQUIRED_METADATA_FIELDS, "metadata", errors)

    topology = _mapping(record.get("topology_contract"), "topology_contract", errors)
    _validate_stateful_fields(topology, RUNTIME_TOPOLOGY_FIELDS, "topology_contract", errors)

    if contract_state == "ws04_01d_final_evidence":
        _validate_ws04_01d_final_evidence(record, metadata, topology, errors)
    else:
        errors.extend(validate_budget_evidence(record, require_final_values=False))
        errors.extend(validate_role_grant_contract(record))

    handoff = _mapping(record.get("handoff"), "handoff", errors)
    if handoff.get("mandatory_follow_up") != "WS04-01D":
        errors.append("handoff.mandatory_follow_up must be WS04-01D")
    required_before = handoff.get("required_before")
    if not isinstance(required_before, list) or "CLOSE-01" not in required_before:
        errors.append("handoff.required_before must include CLOSE-01")

    if contract_state == "provider_independent_template":
        _validate_provider_independent_template(record, metadata, topology, errors)

    errors.extend(detect_sensitive_values(record))
    return errors


def validate_budget_evidence(
    record: Mapping[str, Any],
    *,
    require_final_values: bool,
) -> list[str]:
    errors: list[str] = []
    budget_model = _mapping(record.get("budget_model"), "budget_model", errors)
    inputs = _mapping(budget_model.get("inputs"), "budget_model.inputs", errors)

    resolved_values: dict[str, int] = {}
    for field in BUDGET_INPUT_FIELDS:
        entry = _mapping(inputs.get(field), f"budget_model.inputs.{field}", errors)
        state = entry.get("evidence_state")
        value = entry.get("value")
        if state not in EVIDENCE_STATES:
            errors.append(f"{field} has unsupported evidence_state: {state!r}")
            continue

        if not require_final_values:
            if value is not None:
                errors.append(f"{field} must not contain final values before WS04-01D")
            continue

        if state == "verified":
            if not _is_non_negative_int(value):
                errors.append(f"{field} verified value must be a non-negative integer")
                continue
            if not _evidence_metadata_present(entry.get("evidence")):
                errors.append(f"{field} verified value requires source metadata")
            if value == 0 and not _non_empty_text(entry.get("zero_reason")):
                errors.append(f"{field} zero value requires absence evidence")
            resolved_values[field] = value
        elif state == "not_applicable":
            if value not in (None, 0):
                errors.append(f"{field} not_applicable value must be omitted or zero")
            if not _non_empty_text(entry.get("zero_reason")):
                errors.append(f"{field} not_applicable requires an absence reason")
            resolved_values[field] = 0
        else:
            errors.append(f"{field} final verification cannot use state {state!r}")

    limit_basis = _mapping(budget_model.get("limit_basis"), "budget_model.limit_basis", errors)
    _validate_stateful_fields(
        limit_basis,
        REQUIRED_LIMIT_BASIS_FIELDS,
        "budget_model.limit_basis",
        errors,
    )
    if require_final_values:
        _validate_final_stateful_fields(
            limit_basis,
            REQUIRED_LIMIT_BASIS_FIELDS,
            "budget_model.limit_basis",
            errors,
        )

    mutable_inputs = _mapping(
        budget_model.get("mutable_capacity_inputs"),
        "budget_model.mutable_capacity_inputs",
        errors,
    )
    for field in MUTABLE_CAPACITY_INPUT_FIELDS:
        capacity_entry = _mapping(
            mutable_inputs.get(field),
            f"budget_model.mutable_capacity_inputs.{field}",
            errors,
        )
        _validate_stateful_fields(
            capacity_entry,
            MUTABLE_CAPACITY_REQUIREMENTS,
            f"budget_model.mutable_capacity_inputs.{field}",
            errors,
        )
        if require_final_values:
            _validate_final_stateful_fields(
                capacity_entry,
                MUTABLE_CAPACITY_REQUIREMENTS,
                f"budget_model.mutable_capacity_inputs.{field}",
                errors,
            )

    if require_final_values:
        telemetry_plan = _mapping(
            budget_model.get("telemetry_plan"),
            "budget_model.telemetry_plan",
            errors,
        )
        _validate_final_telemetry_plan(telemetry_plan, errors)

    if not require_final_values or errors:
        return errors

    calculated = calculate_connection_budget(resolved_values)
    reported = _mapping(
        budget_model.get("reported_calculations"),
        "budget_model.reported_calculations",
        errors,
    )
    for field, expected in calculated.as_dict().items():
        if reported.get(field) != expected:
            errors.append(f"{field} does not match calculated value {expected}")
    if calculated.total_budgeted_peak_connections > resolved_values["usable_provider_connection_capacity"]:
        errors.append("total budgeted peak connections exceed usable provider capacity")
    if calculated.remaining_headroom < 0:
        errors.append("remaining headroom must not be negative")

    return errors


def validate_role_grant_contract(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = _mapping(record.get("role_grant_contract"), "role_grant_contract", errors)

    role_classes = _mapping(contract.get("role_classes"), "role_grant_contract.role_classes", errors)
    for role_class in ROLE_CLASSES:
        entry = _mapping(
            role_classes.get(role_class),
            f"role_grant_contract.role_classes.{role_class}",
            errors,
        )
        if entry.get("required") is not True:
            errors.append(f"{role_class} role class must be required")

    checks = contract.get("required_checks")
    if not isinstance(checks, list):
        errors.append("role_grant_contract.required_checks must be a list")
    else:
        missing = sorted(set(ROLE_CHECKS) - {item for item in checks if isinstance(item, str)})
        errors.extend(f"missing role/grant check: {item}" for item in missing)

    forbidden = contract.get("application_runtime_prohibited_capabilities")
    if not isinstance(forbidden, list):
        errors.append("application_runtime_prohibited_capabilities must be a list")
    else:
        missing = sorted(set(APPLICATION_RUNTIME_FORBIDDEN_FLAGS) - {item for item in forbidden if isinstance(item, str)})
        errors.extend(f"missing application runtime prohibited capability: {item}" for item in missing)

    return errors


def validate_final_role_grant_evidence(record: Mapping[str, Any]) -> list[str]:
    errors = validate_role_grant_contract(record)
    contract = _mapping(record.get("role_grant_contract"), "role_grant_contract", errors)
    final_evidence = _mapping(contract.get("final_evidence"), "role_grant_contract.final_evidence", errors)
    application = _mapping(
        final_evidence.get("application_runtime"),
        "role_grant_contract.final_evidence.application_runtime",
        errors,
    )
    migration = _mapping(
        final_evidence.get("migration_execution"),
        "role_grant_contract.final_evidence.migration_execution",
        errors,
    )

    for flag in APPLICATION_RUNTIME_FORBIDDEN_FLAGS:
        if application.get(flag) is not False:
            errors.append(f"application runtime role must not have {flag}")

    if not _non_empty_text(application.get("safe_alias")):
        errors.append("application runtime role requires a safe alias")
    if not _non_empty_text(migration.get("safe_alias")):
        errors.append("migration execution role requires a safe alias")
    if application.get("safe_alias") == migration.get("safe_alias"):
        errors.append("application and migration effective roles must be distinct")

    seen_aliases: dict[str, str] = {}
    for role_class in ROLE_CLASSES:
        path = f"role_grant_contract.final_evidence.{role_class}"
        entry = _mapping(final_evidence.get(role_class), path, errors)
        state = entry.get("state")
        if state == "not_applicable":
            if role_class in FINAL_ROLE_REQUIRED_PRESENT_CLASSES:
                errors.append(f"{role_class} final role evidence cannot be not_applicable")
            if not _non_empty_text(entry.get("reason")):
                errors.append(f"{role_class} not_applicable role evidence requires a reason")
            continue

        if state != "verified":
            errors.append(f"{role_class} final role evidence must be verified or not_applicable")
            continue

        alias = entry.get("safe_alias")
        if not _non_empty_text(alias):
            errors.append(f"{role_class} final role evidence requires a safe alias")
        elif alias in seen_aliases and role_class in {
            "application_runtime",
            "migration_execution",
        }:
            errors.append(
                "application and migration effective roles must be distinct"
            )
        elif _non_empty_text(alias):
            seen_aliases[alias] = role_class

        if not _evidence_metadata_present(entry.get("evidence")):
            errors.append(f"{role_class} final role evidence requires source metadata")

        completed_checks = entry.get("completed_checks")
        if not isinstance(completed_checks, list):
            errors.append(f"{role_class} final role evidence requires completed_checks")
            continue
        missing = sorted(
            set(FINAL_ROLE_EVIDENCE_CHECKS)
            - {item for item in completed_checks if isinstance(item, str)}
        )
        errors.extend(
            f"{role_class} final role evidence missing completed check: {item}"
            for item in missing
        )

    return errors


def detect_sensitive_values(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            findings.extend(detect_sensitive_values(item, f"{path}.{key}"))
        return findings
    if isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(detect_sensitive_values(item, f"{path}[{index}]"))
        return findings
    if not isinstance(value, str):
        return findings

    for label, pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.search(value):
            findings.append(f"sensitive {label} pattern at {path}")
    return findings


def _validate_stateful_fields(
    values: Mapping[str, Any],
    required_fields: tuple[str, ...],
    path: str,
    errors: list[str],
) -> None:
    for field in required_fields:
        if field not in values:
            errors.append(f"missing {path}.{field}")
            continue
        if (
            field == "open_gaps"
            and isinstance(values[field], Mapping)
            and values[field].get("state", values[field].get("evidence_state")) in EVIDENCE_STATES
            and "value" in values[field]
        ):
            continue
        if not _stateful_field_is_populated(values[field]):
            errors.append(f"{path}.{field} must be populated, deferred, or not_applicable with reason")


def _validate_provider_independent_template(
    record: Mapping[str, Any],
    metadata: Mapping[str, Any],
    topology: Mapping[str, Any],
    errors: list[str],
) -> None:
    for field in C_TEMPLATE_DEFERRED_METADATA_FIELDS:
        _require_deferred_null(
            metadata.get(field),
            f"metadata.{field}",
            errors,
        )

    for field in RUNTIME_TOPOLOGY_FIELDS:
        _require_deferred_null(
            topology.get(field),
            f"topology_contract.{field}",
            errors,
        )

    budget_model = _mapping(record.get("budget_model"), "budget_model", errors)
    inputs = _mapping(budget_model.get("inputs"), "budget_model.inputs", errors)
    for field in BUDGET_INPUT_FIELDS:
        entry = _mapping(inputs.get(field), f"budget_model.inputs.{field}", errors)
        if entry.get("evidence_state") != "deferred_to_ws04_01d":
            errors.append(
                f"budget_model.inputs.{field} must remain deferred to WS04-01D "
                "in provider-independent template"
            )
        if entry.get("value") is not None:
            errors.append(f"budget_model.inputs.{field}.value must be null before WS04-01D")

    reported = _mapping(
        budget_model.get("reported_calculations"),
        "budget_model.reported_calculations",
        errors,
    )
    for field, value in reported.items():
        if value is not None:
            errors.append(f"budget_model.reported_calculations.{field} must be null before WS04-01D")

    limit_basis = _mapping(budget_model.get("limit_basis"), "budget_model.limit_basis", errors)
    for field in REQUIRED_LIMIT_BASIS_FIELDS:
        _require_deferred_null(
            limit_basis.get(field),
            f"budget_model.limit_basis.{field}",
            errors,
        )

    mutable_inputs = _mapping(
        budget_model.get("mutable_capacity_inputs"),
        "budget_model.mutable_capacity_inputs",
        errors,
    )
    for field in MUTABLE_CAPACITY_INPUT_FIELDS:
        capacity_entry = _mapping(
            mutable_inputs.get(field),
            f"budget_model.mutable_capacity_inputs.{field}",
            errors,
        )
        for requirement in MUTABLE_CAPACITY_REQUIREMENTS:
            _require_deferred_null(
                capacity_entry.get(requirement),
                f"budget_model.mutable_capacity_inputs.{field}.{requirement}",
                errors,
            )

    telemetry_plan = _mapping(
        budget_model.get("telemetry_plan"),
        "budget_model.telemetry_plan",
        errors,
    )
    if telemetry_plan.get("state") != "deferred_to_ws04_01d":
        errors.append(
            "budget_model.telemetry_plan must remain deferred to WS04-01D "
            "in provider-independent template"
        )

    contract = _mapping(record.get("role_grant_contract"), "role_grant_contract", errors)
    role_classes = _mapping(contract.get("role_classes"), "role_grant_contract.role_classes", errors)
    for role_class in ROLE_CLASSES:
        entry = _mapping(
            role_classes.get(role_class),
            f"role_grant_contract.role_classes.{role_class}",
            errors,
        )
        if entry.get("state") != "deferred_to_ws04_01d":
            errors.append(
                f"role_grant_contract.role_classes.{role_class} must remain "
                "deferred to WS04-01D in provider-independent template"
            )
    if contract.get("final_evidence"):
        errors.append("role_grant_contract.final_evidence must not be populated before WS04-01D")


def _validate_ws04_01d_final_evidence(
    record: Mapping[str, Any],
    metadata: Mapping[str, Any],
    topology: Mapping[str, Any],
    errors: list[str],
) -> None:
    for field in FINAL_METADATA_VALUE_FIELDS:
        _require_verified_value(
            metadata.get(field),
            f"metadata.{field}",
            errors,
            require_source_metadata=False,
        )

    open_gaps = _mapping(metadata.get("open_gaps"), "metadata.open_gaps", errors)
    if open_gaps.get("state") != "verified":
        errors.append("metadata.open_gaps must be verified for final evidence")
    open_gap_values = open_gaps.get("value")
    if not isinstance(open_gap_values, list):
        errors.append("metadata.open_gaps.value must be a list for final evidence")
    elif open_gap_values:
        errors.append("metadata.open_gaps must be empty for final evidence")

    raw_reference = _mapping(
        metadata.get("raw_evidence_location_reference"),
        "metadata.raw_evidence_location_reference",
        errors,
    )
    raw_state = raw_reference.get("state")
    if raw_state == "verified":
        if not _stateful_field_is_populated(raw_reference):
            errors.append("metadata.raw_evidence_location_reference verified value must be populated")
    elif raw_state == "not_applicable":
        if not _non_empty_text(raw_reference.get("reason")):
            errors.append("metadata.raw_evidence_location_reference not_applicable requires a reason")
    else:
        errors.append(
            "metadata.raw_evidence_location_reference must be verified or "
            "not_applicable for final evidence"
        )

    for field in REQUIRED_FINAL_TOPOLOGY_FIELDS:
        _require_verified_value(
            topology.get(field),
            f"topology_contract.{field}",
            errors,
            require_source_metadata=True,
        )
    connection_mode = _mapping(
        topology.get("connection_mode"),
        "topology_contract.connection_mode",
        errors,
    )
    mode_value = connection_mode.get("value")
    if mode_value not in CONNECTION_MODE_VALUES:
        errors.append("topology_contract.connection_mode.value is not allowed")

    pooler_fields_required = mode_value in {"provider_pooler", "proxy"}
    for field in CONDITIONAL_POOLER_TOPOLOGY_FIELDS:
        if pooler_fields_required:
            _require_verified_value(
                topology.get(field),
                f"topology_contract.{field}",
                errors,
                require_source_metadata=True,
            )
        else:
            _require_verified_value_or_not_applicable(
                topology.get(field),
                f"topology_contract.{field}",
                errors,
                require_source_metadata=True,
            )

    errors.extend(validate_budget_evidence(record, require_final_values=True))
    errors.extend(validate_final_role_grant_evidence(record))


def _require_deferred_null(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append(f"{path} must be an object")
        return
    state = value.get("state", value.get("evidence_state"))
    if state != "deferred_to_ws04_01d":
        errors.append(
            f"{path} must remain deferred to WS04-01D in "
            "provider-independent template"
        )
    if value.get("value") is not None:
        errors.append(f"{path}.value must be null before WS04-01D")


def _require_verified_value(
    value: Any,
    path: str,
    errors: list[str],
    *,
    require_source_metadata: bool,
) -> None:
    entry = _mapping(value, path, errors)
    if entry.get("state", entry.get("evidence_state")) != "verified":
        errors.append(f"{path} must be verified for final evidence")
        return
    if not _stateful_field_is_populated(entry):
        errors.append(f"{path} verified value must be populated")
    if require_source_metadata and not _evidence_metadata_present(entry.get("evidence")):
        errors.append(f"{path} verified evidence requires source metadata")


def _require_verified_value_or_not_applicable(
    value: Any,
    path: str,
    errors: list[str],
    *,
    require_source_metadata: bool,
) -> None:
    entry = _mapping(value, path, errors)
    state = entry.get("state", entry.get("evidence_state"))
    if state == "not_applicable":
        if entry.get("value") not in (None, ""):
            errors.append(f"{path} not_applicable value must be omitted")
        if not _non_empty_text(entry.get("reason")):
            errors.append(f"{path} not_applicable requires a reason")
        return
    if state != "verified":
        errors.append(f"{path} must be verified or not_applicable for final evidence")
        return
    if not _stateful_field_is_populated(entry):
        errors.append(f"{path} verified value must be populated")
    if require_source_metadata and not _evidence_metadata_present(entry.get("evidence")):
        errors.append(f"{path} verified evidence requires source metadata")


def _validate_final_stateful_fields(
    values: Mapping[str, Any],
    required_fields: tuple[str, ...],
    path: str,
    errors: list[str],
) -> None:
    for field in required_fields:
        entry = _mapping(values.get(field), f"{path}.{field}", errors)
        if entry.get("state", entry.get("evidence_state")) != "verified":
            errors.append(f"{path}.{field} must be verified for final evidence")
            continue
        if not _stateful_field_is_populated(entry):
            errors.append(f"{path}.{field} verified evidence must be populated")
        if not _evidence_metadata_present(entry.get("evidence")):
            errors.append(f"{path}.{field} verified evidence requires source metadata")


def _validate_final_telemetry_plan(
    telemetry_plan: Mapping[str, Any],
    errors: list[str],
) -> None:
    if telemetry_plan.get("state") != "verified":
        errors.append("budget_model.telemetry_plan must be verified for final evidence")
    signals = telemetry_plan.get("required_signals")
    if not isinstance(signals, list) or not all(_non_empty_text(item) for item in signals):
        errors.append("budget_model.telemetry_plan requires populated required_signals")
    if not _non_empty_text(telemetry_plan.get("dashboard_alert_owner")):
        errors.append("budget_model.telemetry_plan requires dashboard_alert_owner")
    if not _evidence_metadata_present(telemetry_plan.get("evidence")):
        errors.append("budget_model.telemetry_plan verified evidence requires source metadata")


def _stateful_field_is_populated(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if not isinstance(value, Mapping):
        return value is not None

    state = value.get("state", value.get("evidence_state"))
    if state not in EVIDENCE_STATES:
        return False
    if state == "not_applicable":
        return _non_empty_text(value.get("reason"))
    if state in {"blocked", "deferred_to_ws04_01d", "stale", "unverified"}:
        return _non_empty_text(value.get("reason")) or _non_empty_text(value.get("open_gap")) or "value" in value

    field_value = value.get("value", value.get("safe_alias"))
    if isinstance(field_value, list):
        return bool(field_value)
    return field_value is not None and (not isinstance(field_value, str) or bool(field_value.strip()))


def _evidence_metadata_present(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    required = (
        "source_type",
        "date_collected",
        "reviewer",
        "purpose",
        "supported_control_or_pass",
        "sanitized_evidence_reference",
    )
    return all(_non_empty_text(value.get(field)) for field in required)


def _mapping(value: Any, path: str, errors: list[str]) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    errors.append(f"{path} must be an object")
    return {}


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
