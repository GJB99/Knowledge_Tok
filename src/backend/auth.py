from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from .database import get_db
from .models import User

# Security configuration
import os
import secrets

SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32) # Load from environment variable or generate
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token") # Changed tokenUrl to just "/token"

async def authenticate_user(username_or_email: str, password: str, db: AsyncSession):
    """
    Authenticates a user by username or email and password.
    """
    try:
        query = select(User).where(
            or_(
                User.username == username_or_email,
                User.email == username_or_email
            )
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return None # User not found

        if not pwd_context.verify(password, user.hashed_password):
            return None # Incorrect password

        return user # Authentication successful

    except Exception as e:
        print(f"Error in authenticate_user: {e}")
        return None

async def get_user(db: AsyncSession, username: str):
    """
    Fetches a user from the database by username.
    """
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        print(f"JWT Decode Error: {e}") # Log JWT decode errors
        raise credentials_exception

    user = await get_user(db, username=username) # Ensure it's calling get_user here
    if user is None:
        raise credentials_exception
    return user

# auth = Auth() # Instantiate Auth class - No longer needed 