from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services import auth_service
from app.schemas.response import StandardResponse

router = APIRouter(prefix="/auth")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=StandardResponse[dict])
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Public registration always creates a patient account.

    Privileged roles must be provisioned through an authenticated administrative
    workflow. Never trust a role supplied by an unauthenticated client.
    """
    existing_user = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    new_user = models.User(
        username=username,
        email=email,
        hashed_password=auth_service.hash_password(password),
        role="patient",
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger("auth").exception(
            "Database transaction failed during registration: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to a database error.",
        )

    return StandardResponse(
        status="success",
        message="User registered successfully",
        data={"username": new_user.username, "role": new_user.role},
    )


@router.post("/login", response_model=StandardResponse[dict])
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not auth_service.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "type": "access"}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.username, "type": "refresh"}
    )

    return StandardResponse(
        status="success",
        message="Login successful",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
        },
    )


@router.post("/refresh", response_model=StandardResponse[dict])
async def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        payload = auth_service.jwt.decode(
            refresh_token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except auth_service.jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access_token = auth_service.create_access_token(
        data={"sub": user.username, "type": "access"}
    )
    return StandardResponse(
        status="success",
        message="Token refreshed",
        data={
            "access_token": new_access_token,
            "token_type": "bearer",
        },
    )
