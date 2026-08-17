from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_NETWORK_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "urllib.request",
        "socket",
        "stripe",
        "firebase_admin",
        "boto3",
        "botocore",
        "smtplib",
        "sendgrid",
        "twilio",
        "google",
    }
)
_ALLOWED_RUNTIME_BOUNDARIES = {
    "stripe": {"backend/services/stripe_service.py"},
    "firebase_admin": {"backend/firebase_admin_client.py"},
    "boto3": {"backend/services/r2_storage_service.py"},
    "botocore": {"backend/services/r2_storage_service.py"},
}
_ALLOWED_TOOLING = {
    "firebase_admin": {
        "backend/scripts/bootstrap_admin.py",
        "backend/scripts/seed_dev_auth_users.py",
        "backend/scripts/seed_manual_test_users.py",
    }
}


@dataclass(frozen=True)
class _NetworkHit:
    path: str
    module: str
    detail: str


def _production_python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _BACKEND_ROOT.rglob("*.py")
            if "tests" not in path.relative_to(_BACKEND_ROOT).parts
            and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
            and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
            and "alembic" not in path.relative_to(_BACKEND_ROOT).parts
        )
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _matched_network_module(module_name: str) -> str | None:
    for candidate in _NETWORK_MODULES:
        if module_name == candidate or module_name.startswith(f"{candidate}."):
            return candidate
    return None


def _network_hits(path: Path) -> list[_NetworkHit]:
    relative_path = str(path.relative_to(_REPO_ROOT))
    tree = ast.parse(path.read_text(), filename=relative_path)
    aliases: dict[str, str] = {}
    hits: list[_NetworkHit] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                matched = _matched_network_module(alias.name)
                if matched is not None:
                    aliases[alias.asname or alias.name.split(".", maxsplit=1)[0]] = matched
                    hits.append(_NetworkHit(relative_path, matched, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            matched = _matched_network_module(node.module)
            if matched is not None:
                for alias in node.names:
                    aliases[alias.asname or alias.name] = matched
                hits.append(_NetworkHit(relative_path, matched, f"from {node.module} import"))
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name is None:
                continue
            root_name = name.split(".", maxsplit=1)[0]
            matched = aliases.get(root_name)
            if matched is not None:
                hits.append(_NetworkHit(relative_path, matched, name))
    return hits


def _registry_operations() -> set[str]:
    return {
        policy.operation
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }


@pytest.mark.requirement("WS02-04C2-R3")
def test_current_runtime_provider_network_boundaries_are_classified() -> None:
    unclassified: list[_NetworkHit] = []
    for path in _production_python_files():
        for hit in _network_hits(path):
            runtime_paths = _ALLOWED_RUNTIME_BOUNDARIES.get(hit.module, set())
            tooling_paths = _ALLOWED_TOOLING.get(hit.module, set())
            if hit.path not in runtime_paths and hit.path not in tooling_paths:
                unclassified.append(hit)

    assert unclassified == []


@pytest.mark.requirement("WS02-04C2-R3", "WS02-04C2-R4")
def test_current_provider_wrapper_operations_have_retry_policy_entries() -> None:
    assert _registry_operations() >= {
        "stripe.customer.create",
        "stripe.setup_intent.create",
        "stripe.setup_intent.retrieve",
        "stripe.payment_method.retrieve",
        "stripe.payment_method.detach",
        "stripe.customer.default_payment_method.set",
        "stripe.customer.default_payment_method.clear",
        "stripe.payment_intent.create",
        "stripe.payment_intent.confirm",
        "stripe.payment_intent.retrieve",
        "stripe.refund.create",
        "stripe.refund.retrieve",
        "firebase.app_check.verify",
        "firebase.token.verify",
        "firebase.user.lookup",
        "firebase.user.delete",
        "r2.metadata.head",
        "stripe.webhook.delivery",
        "admin_money.refund.retry",
        "admin_money.refund.reconcile",
        "admin_money.credit.retry",
    }

    for operation in (
        "stripe.setup_intent.retrieve",
        "stripe.payment_method.retrieve",
        "stripe.payment_intent.retrieve",
        "stripe.refund.retrieve",
        "r2.metadata.head",
        "firebase.app_check.verify",
        "firebase.token.verify",
    ):
        policy = retry_policy.policy_by_operation(operation)
        assert policy.safety_class == retry_policy.RetrySafetyClass.SAFE_READ
        assert policy.read_operation
        assert not policy.provider_mutation

    app_check_policy = retry_policy.policy_by_operation("firebase.app_check.verify")
    assert app_check_policy.workflow_context == "app_check_request_verification"
    assert app_check_policy.material_callers == (
        "backend.firebase_admin_client.verify_firebase_app_check_token",
    )
    assert app_check_policy.application_automatic_retry_allowed is False
    assert "provider_unavailable" in app_check_policy.current_recovery
    assert "request replay" in app_check_policy.current_recovery
    assert "mutation replay" in app_check_policy.current_recovery


@pytest.mark.requirement("WS02-04C2-R3", "WS02-04C2-R5", "WS02-04C2-R6")
def test_current_stripe_mutation_callers_have_workflow_specific_contexts() -> None:
    contexts = {
        policy.workflow_context
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
        if policy.provider == "stripe"
    }

    assert contexts >= {
        "saved_card_customer_creation",
        "saved_card_setup_intent_creation",
        "checkout_initial_create_before_provider_result",
        "checkout_initial_confirm_after_checkpoint",
        "checkout_existing_pending_confirm_after_provider_read",
        "community_publish_fee_initial_create",
        "community_publish_fee_confirm_after_checkpoint",
        "waitlist_auto_promotion_create",
        "waitlist_auto_promotion_confirm",
        "admin_refund_retry",
        "official_game_cancellation_refund",
        "official_player_removal_refund",
        "late_checkout_payment_refund",
        "community_publish_financial_outcome_refund",
        "user_visible_saved_card_detach",
        "account_deletion_saved_card_cleanup",
        "unpersisted_best_effort_payment_method_cleanup",
        "saved_card_default_set",
        "saved_card_default_clear",
    }


@pytest.mark.requirement("WS02-04C2-R3")
def test_r2_presigning_and_browser_upload_are_not_counted_as_backend_provider_retry() -> None:
    source = (_REPO_ROOT / "backend/services/r2_storage_service.py").read_text()

    assert "head_object" in source
    assert "generate_presigned_url" in source
    assert retry_policy.policy_by_operation("r2.metadata.head").read_operation
    assert "r2.presigned_url.generate" not in _registry_operations()
    assert "direct browser upload" not in {
        policy.workflow_context
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }
