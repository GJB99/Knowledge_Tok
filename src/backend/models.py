from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base  # Import Base from database.py

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

    def __repr__(self):
        return f"<User(username='{self.username}')>"

class Interest(Base):
    __tablename__ = 'interests'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String)

    def __repr__(self):
        return f"<Interest(name='{self.name}')>"

class Content(Base):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    abstract = Column(String)
    source = Column(String)
    external_id = Column(String, unique=True)
    url = Column(String)
    published_date = Column(DateTime)
    paper_metadata = Column(JSON, nullable=True)
    embedding = Column(JSON, nullable=True)
    
    # Relationships
    interactions = relationship("Interaction", back_populates="content")

    def __repr__(self):
        return f"<Content(title='{self.title}')>"

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

    def __repr__(self):
        return f"<Interaction(user_id={self.user_id}, content_id={self.content_id}, type='{self.interaction_type}')>" 