import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def build_conflict_detail(exc: IntegrityError) -> str:
    # Map known unique-constraint failures to clearer API messages so Postman
    # responses are easier to understand during development.
    error_text = str(exc.orig)

    constraint_messages = {
        "uq_users_auth_user_id": "A user with this auth_user_id already exists.",
        "uq_users_email": "A user with this email already exists.",
        "uq_users_phone": "A user with this phone already exists.",
        "uq_users_stripe_customer_id": (
            "A user with this stripe_customer_id already exists."
        ),
    }

    for constraint_name, message in constraint_messages.items():
        if constraint_name in error_text:
            return message

    return error_text


# This route returns all user profiles currently stored in the app database.
@router.get("", response_model=list[UserRead], status_code=status.HTTP_200_OK)
def list_users(db: Session = Depends(get_db)) -> list[User]:
    users = db.scalars(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
    ).all()
    return list(users)


# This route creates an app-level user profile after the client has already
# authenticated the person through Firebase Auth.
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> User:
    new_user = User(
        id=uuid.uuid4(),
        auth_user_id=user.auth_user_id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        profile_photo_url=user.profile_photo_url,
        home_city=user.home_city,
        home_state=user.home_state,
        stripe_customer_id=user.stripe_customer_id,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        db.rollback()
        # Surface the database failure more honestly so local API testing is
        # easier to debug while the error handling layer is still minimal.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return new_user


# This route fetches a single user profile by the app's internal UUID.
@router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


# This route applies partial updates to an existing user profile.
@router.patch("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_user(
    user_id: uuid.UUID, user_update: UserUpdate, db: Session = Depends(get_db)
) -> User:
    db_user = db.get(User, user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    update_data = user_update.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(db_user, field_name, field_value)

    # Keep updated_at aligned with the latest profile change so downstream
    # clients can reliably track when the record was last modified.
    db_user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return db_user


# This route performs a soft delete so the user record remains in the database
# for history and audit purposes.
@router.delete("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    db_user = db.get(User, user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    db_user.account_status = "deleted"
    db_user.updated_at = datetime.now(timezone.utc)
    db_user.deleted_at = datetime.now(timezone.utc)

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return db_user
