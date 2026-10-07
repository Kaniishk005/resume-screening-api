from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (create_access_token, hash_password,
                               verify_password)
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse
import secrets
import string
from app.core.constants import (
    GUEST_EMAIL,
    GUEST_NAME
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def generate_random_password(length: int = 32):

    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )

@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.scalar(select(User).where(User.email == user.email))

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already registered.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to register user.") from exc

    return new_user

@router.post("/guest", response_model=Token)
def guest_login(db: Session = Depends(get_db)):

    guest = db.scalar(
        select(User).where(User.email == GUEST_EMAIL)
    )

    if guest is None:

        password = generate_random_password()

        guest = User(
            username=GUEST_NAME,
            email=GUEST_EMAIL,
            hashed_password=hash_password(password),
        )

        try:
            db.add(guest)
            db.commit()
            db.refresh(guest)
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail="Unable to create guest account.") from exc

    access_token = create_access_token(
        data={"sub": guest.email},
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    db_user = db.scalar(select(User).where(User.email == form_data.username))

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}
