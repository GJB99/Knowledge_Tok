from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, JSON
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# Association table for user interests
user_interests = Table(
    'user_interests',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('interest_id', Integer, ForeignKey('interests.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    
    # Relationships
    interests = relationship("Interest", secondary=user_interests)
    interactions = relationship("Interaction", back_populates="user")

class Interest(Base):
    __tablename__ = 'interests'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String)

class Content(Base):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    abstract = Column(String)
    source = Column(String, nullable=False)  # arxiv, core, etc.
    external_id = Column(String)
    url = Column(String)
    published_date = Column(DateTime)
    paper_metadata = Column(JSON)
    
    # Relationships
    interactions = relationship("Interaction", back_populates="content")

class Interaction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    interaction_type = Column(String)  # like, save, view
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    content = relationship("Content", back_populates="interactions") 