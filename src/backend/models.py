from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Create Base here instead of importing
Base = declarative_base()

# Association table for user interests
user_interests = Table(
    'user_interests',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('interest_id', Integer, ForeignKey('interests.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
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
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    abstract = Column(Text)
    source = Column(String)
    external_id = Column(String)
    url = Column(String)
    published_date = Column(DateTime)
    paper_metadata = Column(JSON)
    
    # Relationships
    interactions = relationship("Interaction", back_populates="content")

class Interaction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    interaction_type = Column(String)  # 'like' or 'save'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    content = relationship("Content", back_populates="interactions") 