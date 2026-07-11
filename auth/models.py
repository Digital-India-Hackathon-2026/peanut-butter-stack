"""Pydantic request/response models for authentication endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from auth.types import Role


class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: Role = "nurse"


class UserSignin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    role: Role = "nurse"


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    email: str
    role: Role


class UserProfile(BaseModel):
    email: str
    role: Role


class MessageResponse(BaseModel):
    message: str
