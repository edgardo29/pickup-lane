from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import User, UserSettings, UserStats
from backend.scripts.demo_data.helpers import now_utc
from backend.scripts.demo_data.users import CURRENT_USER_KEY


def seed_user_profile_context(
    db: Session, users: dict[str, User]
) -> tuple[UserSettings, UserStats]:
    timestamp = now_utc()
    current_user = users[CURRENT_USER_KEY]

    settings = db.get(UserSettings, current_user.id)
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    settings.push_notifications_enabled = True
    settings.email_notifications_enabled = True
    settings.sms_notifications_enabled = False
    settings.marketing_opt_in = False
    settings.location_permission_status = "allowed"
    settings.selected_city = "Chicago"
    settings.selected_state = "IL"
    settings.updated_at = timestamp

    stats = db.get(UserStats, current_user.id)
    if stats is None:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)

    stats.games_played_count = 18
    stats.games_hosted_completed_count = 3
    stats.no_show_count = 0
    stats.late_cancel_count = 1
    stats.host_cancel_count = 0
    stats.last_calculated_at = timestamp

    return settings, stats
