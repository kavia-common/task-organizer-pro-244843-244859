from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address (unique).")
    password: str = Field(..., min_length=8, description="User password (min 8 characters).")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type (always 'bearer').")


class UserResponse(BaseModel):
    id: str = Field(..., description="User UUID.")
    email: EmailStr = Field(..., description="User email address.")
    created_at: str = Field(..., description="ISO timestamp when the user was created.")
