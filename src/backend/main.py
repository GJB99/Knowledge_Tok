from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc, Integer
import requests
from .models import Content, User, Interaction, Base
from .database import get_db, init_db, AsyncSessionLocal, get_articles_db, engine
import asyncio
from datetime import datetime, timedelta
from .seed import seed_initial_content
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

import secrets
from dotenv import load_dotenv
import os
import json
import io
from pydantic import BaseModel, EmailStr
from .utils import process_and_store_arxiv_results, get_embedding, similarity_search # Import the functions
from fastapi.staticfiles import StaticFiles
from . import auth
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional
from .auth import authenticate_user

app = FastAPI()

# Load environment variables
load_dotenv()

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    try:
        async with engine.begin() as conn:
            # Only create tables, don't drop them
            await conn.run_sync(Base.metadata.create_all)
                
        # Initialize both main and articles databases
        await init_db()
    except Exception as e:
        print(f"Error during startup: {e}")
        raise e

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email configuration
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_FROM=os.getenv('MAIL_FROM'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', 465)),  # Default to 465 if not set
    MAIL_SERVER=os.getenv('MAIL_SERVER'),
    MAIL_STARTTLS=False,  # Disable STARTTLS since we're using SSL
    MAIL_SSL_TLS=True,    # Enable SSL
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
    TIMEOUT=60
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/backend/static"), name="static")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user storage (replace with database in production)
users = {}

# Add these Pydantic models at the top of the file
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    token: str
    message: Optional[str] = None

class InteractionCreate(BaseModel):
    content_id: int
    interaction_type: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse('src/backend/static/index.html')

@app.get("/favicon.ico")
async def favicon():
    """
    Returns no content for favicon requests.
    """
    return JSONResponse(status_code=204, content={})

@app.get("/search/arxiv")
async def search_arxiv(
    query: str = "machine learning",
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_articles_db)
):
    try:
        # Clean and validate input
        search_terms = [term.strip().lower() for term in query.split() if len(term.strip()) >= 3]
        if not search_terms:
            return {"items": [], "total": 0, "has_more": False}

        # Calculate offset
        offset = (page - 1) * page_size
        
        # --- Keyword Search with Improved Relevance ---
        title_conditions = [Content.title.ilike(f'%{term}%') for term in search_terms]
        abstract_conditions = [Content.abstract.ilike(f'%{term}%') for term in search_terms]

        # Build scoring with higher weight for title matches
        score_expr = func.coalesce(0, 0)
        for term in search_terms:
            title_matches = (func.instr(func.lower(Content.title), term) > 0).cast(Integer) * 3
            abstract_matches = (func.instr(func.lower(Content.abstract), term) > 0).cast(Integer)
            score_expr += title_matches + abstract_matches

        base_query = select(
            Content.id,
            Content.title,
            Content.abstract,
            Content.source,
            Content.external_id,
            Content.url,
            Content.published_date,
            Content.paper_metadata,
            score_expr.label("score")
        ).where(
            or_(*title_conditions, *abstract_conditions)
        ).order_by(
            desc("score"), 
            desc(Content.published_date)
        )

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await db.scalar(count_query)

        # Apply pagination
        paginated_query = base_query.offset(offset).limit(page_size)
        results = await db.execute(paginated_query)
        articles = results.all()

        return {
            "items": format_articles(articles),
            "page": page,
            "total": total,
            "has_more": (offset + page_size) < total
        }

    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/core")
def search_core(query: str, max_results: int = 10):
    """
    A placeholder endpoint for CORE API content retrieval.
    
    In a production application, replace this code with actual API calls to the CORE API,
    process the returned data, and normalize it for your application.
    """
    # This is a placeholder implementation.
    return JSONResponse(content={"result": f"Core API search for query '{query}' with max_results={max_results}"})

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await authenticate_user(form_data.username, form_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print(f"Login error in /token endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )

@app.get("/api/content")
async def get_content(
    page: int = 1, 
    limit: int = 10,
    current_user: Optional[User] = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_articles_db)
):
    try:
        offset = (page - 1) * limit
        
        # Base query for content
        query = select(Content)
        
        # If user is authenticated, exclude content they've interacted with
        if current_user:
            # Get all content IDs the user has interacted with
            interaction_query = select(Interaction.content_id).where(
                Interaction.user_id == current_user.id
            )
            result = await db.execute(interaction_query)
            interacted_content_ids = [row[0] for row in result]
            
            # Exclude content that has been interacted with
            if interacted_content_ids:
                query = query.where(~Content.id.in_(interacted_content_ids))
        
        # Add ordering and pagination
        query = query.order_by(Content.published_date.desc())
        
        # Get total count of filtered content
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        contents = result.scalars().all()
        
        return {
            "items": [
                {
                    "id": content.id,
                    "title": content.title,
                    "abstract": content.abstract,
                    "source": content.source,
                    "url": content.url,
                    "metadata": {
                        "categories": content.paper_metadata.get("categories", []),
                        "published_date": content.published_date.isoformat() if content.published_date else None,
                        "authors": content.paper_metadata.get("authors", []),
                        "paper_id": content.paper_metadata.get("paper_id", "")
                    }
                }
                for content in contents
            ],
            "total": total_count,
            "has_more": offset + limit < total_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(content='''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Login - Academic Feed App</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .auth-form { max-width: 300px; margin: 100px auto; padding: 20px; background: #f5f5f5; border-radius: 8px; }
                .auth-form input { width: 100%; padding: 8px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
                .auth-form button { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
                .auth-links { text-align: center; margin-top: 15px; }
                .auth-links a { color: #3498db; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="auth-form">
                <h2>Login</h2>
                <form onsubmit="event.preventDefault(); handleLogin();">
                    <input type="text" id="username" placeholder="Username" required>
                    <input type="password" id="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
                <div class="auth-links">
                    <p>Don't have an account? <a href="/signup">Sign Up</a></p>
                </div>
            </div>
            <script>
                async function handleLogin() {
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    try {
                        const response = await fetch('/token', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
                        });
                        if (response.ok) {
                            const data = await response.json();
                            localStorage.setItem('token', data.access_token);
                            window.location.href = '/';
                        } else {
                            alert('Invalid credentials');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Login failed');
                    }
                }
            </script>
        </body>
    </html>
    ''')

@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    html_content = '''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Sign Up - Academic Feed App</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background-color: #f0f2f5;
                }
                .auth-form { 
                    max-width: 400px; 
                    margin: 50px auto; 
                    padding: 30px; 
                    background: white; 
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }
                .auth-form h2 {
                    text-align: center;
                    margin-bottom: 30px;
                    color: #1a1a1a;
                }
                .auth-form input { 
                    width: calc(100% - 24px); 
                    padding: 12px;
                    margin: 8px 0 20px 0;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                }
                .auth-form button { 
                    width: 100%; 
                    padding: 12px;
                    background: #3498db;
                    color: white; 
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 500;
                }
                .auth-form button:hover {
                    background: #2980b9;
                }
                .auth-links { 
                    text-align: center; 
                    margin-top: 20px;
                }
                .auth-links a { 
                    color: #3498db; 
                    text-decoration: none;
                    font-weight: 500;
                }
                .auth-links a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <div class="auth-form">
                <h2>Sign Up</h2>
                <form id="signupForm">
                    <input type="email" id="email" placeholder="Email" required>
                    <input type="text" id="username" placeholder="Username" required>
                    <input type="password" id="password" placeholder="Password" required>
                    <button type="submit">Sign Up</button>
                </form>
                <div class="auth-links">
                    <p>Already have an account? <a href="/login">Login</a></p>
                </div>
            </div>
            <script>
                document.getElementById('signupForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const email = document.getElementById('email').value;
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    try {
                        const response = await fetch('/auth/register', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({email, username, password})
                        });
                        if (response.ok) {
                            alert('Registration successful!');
                            window.location.href = '/login';
                        } else {
                            const error = await response.json();
                            alert(error.detail || 'Registration failed');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Registration failed');
                    }
                }
            </script>
        </body>
    </html>
    '''
    return HTMLResponse(content=html_content)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
    return encoded_jwt

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if username or email already exists
    query = select(User).where(
        or_(
            User.username == user.username,
            User.email == user.email
        )
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Generate verification token and create user first
    verification_token = secrets.token_urlsafe(32)
    hashed_password = pwd_context.hash(user.password)
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=False,
        verification_token=verification_token
    )
    
    try:
        verification_url = f"http://localhost:8000/verify/{verification_token}"
        fm = FastMail(mail_config)
        
        message = MessageSchema(
            subject="Welcome to Academic Feed - Please Verify Your Email",
            recipients=[user.email],
            body=f"""
                <html>
                    <head>
                        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/katex/0.15.3/katex.min.css">
                    </head>
                    <body>
                        <p>Hi {user.username},</p>
                        <p>Thank you for registering with Academic Feed. Please click the link below to verify your email address:</p>
                        <p><a href="{verification_url}">Verify Email</a></p>
                        <p>If you did not register for an account, please ignore this email.</p>
                        <p>Best regards,<br>The Academic Feed Team</p>
                    </body>
                </html>
            """,
            subtype="html"
        )
        
        background_tasks = BackgroundTasks()
        background_tasks.add_task(fm.send_message, message)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        # Create a JWT token for the newly registered user
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username}, expires_delta=access_token_expires
        )
        
        return {
            "token": access_token,
            "message": "Registration successful! Please check your email to verify your account."
        }
    except Exception as e:
        await db.rollback()
        print(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again later.")

@app.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.verification_token == token)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Invalid verification token")
        
    if user.is_verified:
        return {"message": "Account already verified"}
        
    user.is_verified = True
    user.verification_token = None  # Clear the token after verification
    await db.commit()
    
    return {"message": "Email verified successfully. You can now log in."}

@app.post("/api/interactions")
async def create_interaction(
    interaction: InteractionCreate,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_articles_db)
):
    # Check for existing interaction
    existing = await db.execute(
        select(Interaction).where(
            and_(
                Interaction.user_id == current_user.id,
                Interaction.content_id == interaction.content_id,
                Interaction.interaction_type == interaction.interaction_type
            )
        )
    )
    existing = existing.scalar_one_or_none()
    
    if existing:
        await db.delete(existing)
        action = "removed"
    else:
        new_interaction = Interaction(
            user_id=current_user.id,
            content_id=interaction.content_id,
            interaction_type=interaction.interaction_type
        )
        db.add(new_interaction)
        action = "added"
    
    await db.commit()
    return {"status": "success", "action": action}

@app.get("/api/user/interactions")
async def get_user_interactions(
    type: str,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_articles_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    # Join interactions with content
    query = select(
        Interaction,
        Content
    ).join(
        Content, Interaction.content_id == Content.id
    ).where(
        and_(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == type
        )
    )
    
    result = await db.execute(query)
    interactions = result.all()
    
    return [
        {
            "interaction_id": interaction.id,
            "interaction_type": interaction.interaction_type,
            "content": {
                "id": content.id,
                "title": content.title,
                "abstract": content.abstract,
                "source": content.source,
                "url": content.url,
                "metadata": {
                    "categories": content.paper_metadata.get("categories", []),
                    "published_date": content.published_date.isoformat() if content.published_date else None,
                    "authors": content.paper_metadata.get("authors", []),
                    "paper_id": content.paper_metadata.get("paper_id", "")
                }
            }
        } for interaction, content in interactions
    ]

@app.get("/api/content/{content_id}")
async def get_content_by_id(content_id: int, db: AsyncSession = Depends(get_articles_db)):
    query = select(Content).where(Content.id == content_id)
    result = await db.execute(query)
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    return {
        "id": content.id,
        "title": content.title,
        "abstract": content.abstract,
        "source": content.source,
        "url": content.url,
        "paper_metadata": content.paper_metadata
    }

@app.get("/feed")
async def get_feed_data(db: AsyncSession = Depends(get_articles_db)):
    try:
        query = select(Content).order_by(Content.published_date.desc()).limit(10)
        result = await db.execute(query)
        content = result.scalars().all()
        
        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "abstract": item.abstract,
                    "source": item.source,
                    "url": item.url,
                    "metadata": item.paper_metadata
                }
                for item in content
            ]
        }
    except Exception as e:
        print(f"Error fetching DB contents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PasswordResetRequest(BaseModel):
    email: str

@app.post("/auth/reset-password-request")
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        await db.commit()
        
        reset_link = f"http://localhost:8000/auth/reset-password/{reset_token}"
        email_content = f"""
        Hello,
        
        You have requested to reset your password. Click the link below to reset it:
        
        {reset_link}
        
        If you didn't request this, please ignore this email.
        
        The link will expire in 24 hours.
        """
        
        # For testing, just print the email content
        print(f"Would send email to {request.email}:\n{email_content}")
        
        # TODO: Implement actual email sending
        # background_tasks.add_task(
        #     send_email,
        #     recipient_email=request.email,
        #     subject="Password Reset Request",
        #     content=email_content
        # )
    
    return {"message": "If an account exists with this email, you will receive password reset instructions."}

@app.post("/auth/reset-password/{token}")
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(
        and_(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        )
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    hashed_password = pwd_context.hash(new_password)
    user.password_hash = hashed_password
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    
    return {"message": "Password reset successful"}

def format_articles(articles):
    return [
        {
            "id": article.id,
            "title": article.title,
            "abstract": article.abstract,
            "source": "arXiv",
            "url": article.url,
            "metadata": {
                "categories": article.paper_metadata.get("categories", []),
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "authors": article.paper_metadata.get("authors", []),
                "paper_id": article.paper_metadata.get("paper_id", "")
            }
        }
        for article in articles
    ]

@app.get("/api/content/{content_id}/interaction-status")
async def get_interaction_status(
    content_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_articles_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Check for existing interactions of different types
    query = select(Interaction).where(
        and_(
            Interaction.user_id == current_user.id,
            Interaction.content_id == content_id
        )
    )
    result = await db.execute(query)
    interactions = result.scalars().all()

    return {
        "isLiked": any(i.interaction_type == "like" for i in interactions),
        "isSaved": any(i.interaction_type == "save" for i in interactions),
        "isNotInterested": any(i.interaction_type == "not_interested" for i in interactions)
    } 