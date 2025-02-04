from .database import Base, engine
from .models import Content, User, Interest, Interaction

# This ensures all models are registered with SQLAlchemy
models = [Content, User, Interest, Interaction] 