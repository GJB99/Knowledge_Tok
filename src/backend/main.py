from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
import requests
from models import Content, User, Interaction
import auth
from database import get_db, init_db, AsyncSessionLocal, get_articles_db
import asyncio
from datetime import datetime, timedelta
from seed import seed_initial_content
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

import secrets
from dotenv import load_dotenv
import os
import json
import io
from pydantic import BaseModel
from utils import process_and_store_arxiv_results
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Load environment variables
load_dotenv()

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    try:
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
    MAIL_USERNAME="guusdoly@guusbouwens.com",
    MAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
    MAIL_FROM="guusdoly@guusbouwens.com",
    MAIL_PORT=587,
    MAIL_SERVER="mail.guusbouwens.com",  # Your Roundcube mail server
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse('static/index.html')

@app.get("/favicon.ico")
async def favicon():
    """
    Returns no content for favicon requests.
    """
    return JSONResponse(status_code=204, content={})

@app.get("/search/arxiv")
async def search_arxiv(
    query: str = "machine learning OR deep learning OR artificial intelligence OR neural networks OR computer vision OR natural language processing",
    max_results: int = 100,
    db: AsyncSession = Depends(get_articles_db)
):
    try:
        # First try to find cached results
        search_terms = query.lower().split()
        cached_query = select(
            Content.id,
            Content.title,
            Content.abstract,
            Content.source,
            Content.external_id,
            Content.url,
            Content.published_date
        ).where(
            or_(*[
                or_(
                    Content.title.ilike(f'%{term}%'),
                    Content.abstract.ilike(f'%{term}%')
                )
                for term in search_terms
            ])
        ).order_by(Content.published_date.desc())
        
        cached_results = await db.execute(cached_query)
        cached_articles = cached_results.all()

        # If we have cached results, return them
        if cached_articles:
            return {
                "items": [
                    {
                        "id": article.id,
                        "title": article.title,
                        "abstract": article.abstract,
                        "source": "arXiv",
                        "url": article.url,
                        "published_date": article.published_date.isoformat() if article.published_date else None
                    }
                    for article in cached_articles[:max_results]
                ],
                "has_more": len(cached_articles) > max_results,
                "total": len(cached_articles)
            }

        # If no cached results or error, fetch from arXiv API
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending"
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail=f"Error fetching from arXiv: {response.status_code}"
            )
        
        stored_articles = await process_and_store_arxiv_results(response.text, db)
        
        return {
            "items": [
                {
                    "id": article.id,
                    "title": article.title,
                    "abstract": article.abstract,
                    "source": "arXiv",
                    "url": article.url,
                    "published_date": article.published_date.isoformat() if article.published_date else None
                }
                for article in stored_articles
            ],
            "has_more": False,
            "total": len(stored_articles)
        }
    except Exception as e:
        print(f"Search error: {str(e)}")
        # If database error occurs, try fetching directly from arXiv
        try:
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending"
            }
            
            response = requests.get(base_url, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error fetching from arXiv: {response.status_code}"
                )
            
            stored_articles = await process_and_store_arxiv_results(response.text, db)
            
            return {
                "items": [
                    {
                        "id": article.id,
                        "title": article.title,
                        "abstract": article.abstract,
                        "source": "arXiv",
                        "url": article.url,
                        "published_date": article.published_date.isoformat() if article.published_date else None
                    }
                    for article in stored_articles
                ],
                "has_more": False,
                "total": len(stored_articles)
            }
        except Exception as nested_e:
            raise HTTPException(status_code=500, detail=str(nested_e))

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
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/content")
async def get_content(
    page: int = 1, 
    limit: int = 10,
    db: AsyncSession = Depends(get_articles_db)
):
    try:
        offset = (page - 1) * limit
        
        # Get total count
        count_query = select(func.count(Content.id))
        total_count = await db.execute(count_query)
        total = total_count.scalar()
        
        # Get paginated content without paper_metadata
        query = select(
            Content.id,
            Content.title,
            Content.abstract,
            Content.source,
            Content.external_id,
            Content.url,
            Content.published_date
        ).order_by(Content.published_date.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        contents = result.all()
        
        return {
            "items": [
                {
                    "id": content.id,
                    "title": content.title,
                    "abstract": content.abstract,
                    "source": content.source,
                    "url": content.url,
                    "published_date": content.published_date.isoformat() if content.published_date else None,
                }
                for content in contents
            ],
            "has_more": (offset + limit) < total,
            "total": total
        }
    except Exception as e:
        print(f"Error fetching content: {str(e)}")
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
                        const response = await fetch('/register', {
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
                });
            </script>
        </body>
    </html>
    '''
    return HTMLResponse(content=html_content)

@app.post("/register")
async def register(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        data = await request.json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        
        if not all([email, username, password]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Check if user exists
        query = select(User).where(
            or_(User.email == email, User.username == username)
        )
        result = await db.execute(query)

        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        # Create new user
        hashed_password = auth.get_password_hash(password)
        verification_token = secrets.token_urlsafe(32)
        new_user = User(
            email=email,
            username=username,

            password_hash=hashed_password,
            is_verified=False,
            verification_token=verification_token
        )
        
        db.add(new_user)
        await db.commit()
        
        return JSONResponse(content={"message": "Registration successful"}, status_code=200)
    except Exception as e:
        await db.rollback()
        return JSONResponse(
            content={"detail": str(e)}, 
            status_code=500
        )

@app.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.verification_token == token)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    user.is_verified = True
    user.verification_token = None
    await db.commit()
    
    return HTMLResponse(content='''
        <html>
            <body>
                <h1>Email verified successfully!</h1>
                <p>You can now <a href="/login">login</a> to your account.</p>
            </body>
        </html>
    ''')

@app.get("/api/user/interactions")
async def get_user_interactions(
    type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    try:
        query = select(Interaction, Content).\
            join(Content).\
            where(
                and_(
                    Interaction.user_id == current_user.id,

                    Interaction.interaction_type == type
                )

            )
        result = await db.execute(query)
        interactions = result.all()
        
        return [
            {
                "id": content.id,
                "title": content.title,
                "abstract": content.abstract,
                "source": content.source,
                "url": content.url,
                "interaction_type": interaction.interaction_type
            }
            for interaction, content in interactions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New Pydantic model for creating interactions
class InteractionCreate(BaseModel):
    content_id: int
    interaction_type: str

# New endpoint to handle like/save interactions from the ContentCard component
@app.post("/api/interactions")
async def handle_interaction(
    interaction: InteractionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    try:
        # Check if interaction already exists

        query = select(Interaction).where(
            and_(
                Interaction.user_id == current_user.id,

                Interaction.content_id == interaction.content_id,
                Interaction.interaction_type == interaction.interaction_type

            )
        )
        result = await db.execute(query)
        existing_interaction = result.scalar_one_or_none()

        if existing_interaction:
            # If interaction exists, remove it (toggle behavior)
            await db.delete(existing_interaction)
        else:
            # Create new interaction
            new_interaction = Interaction(
                user_id=current_user.id,
                content_id=interaction.content_id,
                interaction_type=interaction.interaction_type
            )

            db.add(new_interaction)

        await db.commit()
        return {"success": True, "action": "removed" if existing_interaction else "added"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/db-contents")
async def get_db_contents(db: AsyncSession = Depends(get_articles_db)):
    try:
        # Get all content
        query = select(Content)
        result = await db.execute(query)
        content = result.scalars().all()
        
        return {
            "total_items": len(content),
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "abstract": item.abstract,
                    "source": item.source,
                    "url": item.url,
                    "published_date": item.published_date.isoformat() if item.published_date else None,
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
    
    hashed_password = auth.get_password_hash(new_password)
    user.hashed_password = hashed_password
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    
    return {"message": "Password reset successful"} 