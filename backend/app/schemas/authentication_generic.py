from sqlmodel import Field, SQLModel

# -----------------------------------------------------------------------------
# Authentication and generic API schemas
# -----------------------------------------------------------------------------


 
class Message(SQLModel):
    """Generic API response schema for simple messages."""
    message: str


 
class Token(SQLModel):
    """API response schema: JSON payload returned after successful authentication."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    """Internal/API schema: decoded JWT token contents. `sub` stores the user id."""
    sub: str | None = None

class UpdatePassword(SQLModel):
    """API schema: payload used for changing an existing password."""
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

class NewPassword(SQLModel):
    """API schema: payload used when resetting a password with a token."""
    token: str
    new_password: str = Field(min_length=8, max_length=128)