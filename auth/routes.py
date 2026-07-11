"""FastAPI router for sign-up, sign-in, and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.config import ACCESS_TOKEN_EXPIRE_DELTA
from auth.models import MessageResponse, TokenResponse, UserProfile, UserSignin, UserSignup
from auth.security import create_access_token, decode_access_token
from auth.types import Role

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/signin")


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(payload: UserSignup):
    token = create_access_token(
        {"sub": payload.email, "role": payload.role, "user_id": payload.email},
        expires_delta=ACCESS_TOKEN_EXPIRE_DELTA,
    )
    return TokenResponse(access_token=token, email=payload.email, role=payload.role)


@router.post(
    "/signin",
    response_model=TokenResponse,
    summary="Sign in an existing user",
)
async def signin(payload: UserSignin):
    token = create_access_token(
        {"sub": payload.email, "role": payload.role, "user_id": payload.email},
        expires_delta=ACCESS_TOKEN_EXPIRE_DELTA,
    )
    return TokenResponse(access_token=token, email=payload.email, role=payload.role)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload or "role" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserProfile(email=payload["sub"], role=payload["role"])


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Return the currently authenticated user",
)
async def me(user: UserProfile = Depends(get_current_user)):
    return user


@router.get("/health", response_model=MessageResponse, summary="Auth service health check")
async def auth_health():
    return MessageResponse(message="Auth service is healthy")
