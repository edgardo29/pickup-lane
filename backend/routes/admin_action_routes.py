import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AdminActionCreate, AdminActionNoteCreate, AdminActionRead
from backend.services.admin_action_policy import ADMIN_ACTION_TARGET_FIELDS
from backend.services.admin_action_service import (
    append_admin_action_note,
    create_admin_action,
    get_admin_action_for_viewer_or_404,
    list_admin_actions,
    serialize_admin_action_reads,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/actions", tags=["admin_actions"])


@router.post("", response_model=AdminActionRead, status_code=status.HTTP_201_CREATED)
def create_admin_action_route(
    admin_action: AdminActionCreate,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminActionRead:
    created_action = create_admin_action(
        db,
        admin_user=current_user,
        payload=admin_action,
    )
    return serialize_admin_action_reads(db, [created_action])[0]


@router.get(
    "/{admin_action_id}",
    response_model=AdminActionRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_action_route(
    admin_action_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminActionRead:
    admin_action = get_admin_action_for_viewer_or_404(
        db,
        admin_action_id,
        current_user,
    )
    return serialize_admin_action_reads(db, [admin_action])[0]


@router.post(
    "/{admin_action_id}/notes",
    response_model=AdminActionRead,
    status_code=status.HTTP_201_CREATED,
)
def append_admin_action_note_route(
    admin_action_id: uuid.UUID,
    note: AdminActionNoteCreate,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminActionRead:
    admin_action = append_admin_action_note(
        db,
        admin_user=current_user,
        target_admin_action_id=admin_action_id,
        payload=note,
    )
    return serialize_admin_action_reads(db, [admin_action])[0]


@router.get("", response_model=list[AdminActionRead], status_code=status.HTTP_200_OK)
def list_admin_actions_route(
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = None,
    target_user_id: uuid.UUID | None = None,
    target_game_id: uuid.UUID | None = None,
    target_booking_id: uuid.UUID | None = None,
    target_participant_id: uuid.UUID | None = None,
    target_payment_id: uuid.UUID | None = None,
    target_refund_id: uuid.UUID | None = None,
    target_game_credit_id: uuid.UUID | None = None,
    target_venue_id: uuid.UUID | None = None,
    target_venue_image_id: uuid.UUID | None = None,
    target_message_id: uuid.UUID | None = None,
    target_sub_post_id: uuid.UUID | None = None,
    target_sub_post_request_id: uuid.UUID | None = None,
    target_sub_post_position_id: uuid.UUID | None = None,
    target_sub_chat_message_id: uuid.UUID | None = None,
    target_notification_id: uuid.UUID | None = None,
    target_platform_notice_campaign_id: uuid.UUID | None = None,
    target_admin_action_id: uuid.UUID | None = None,
    target_support_flag_id: uuid.UUID | None = None,
    target_review_case_id: uuid.UUID | None = None,
    target_financial_outcome_id: uuid.UUID | None = None,
    target_host_publish_fee_id: uuid.UUID | None = None,
    target_host_publish_entitlement_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> list[AdminActionRead]:
    target_filter_values = {
        "target_user_id": target_user_id,
        "target_game_id": target_game_id,
        "target_booking_id": target_booking_id,
        "target_participant_id": target_participant_id,
        "target_payment_id": target_payment_id,
        "target_refund_id": target_refund_id,
        "target_game_credit_id": target_game_credit_id,
        "target_venue_id": target_venue_id,
        "target_venue_image_id": target_venue_image_id,
        "target_message_id": target_message_id,
        "target_sub_post_id": target_sub_post_id,
        "target_sub_post_request_id": target_sub_post_request_id,
        "target_sub_post_position_id": target_sub_post_position_id,
        "target_sub_chat_message_id": target_sub_chat_message_id,
        "target_notification_id": target_notification_id,
        "target_platform_notice_campaign_id": target_platform_notice_campaign_id,
        "target_admin_action_id": target_admin_action_id,
        "target_support_flag_id": target_support_flag_id,
        "target_review_case_id": target_review_case_id,
        "target_financial_outcome_id": target_financial_outcome_id,
        "target_host_publish_fee_id": target_host_publish_fee_id,
        "target_host_publish_entitlement_id": target_host_publish_entitlement_id,
    }
    target_filters = {
        field_name: target_filter_values[field_name]
        for field_name in ADMIN_ACTION_TARGET_FIELDS
    }
    admin_actions = list_admin_actions(
        db,
        viewer_user=current_user,
        admin_user_id=admin_user_id,
        action_type=action_type,
        target_filters=target_filters,
        limit=limit,
    )
    return serialize_admin_action_reads(db, admin_actions)
