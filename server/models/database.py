from sqlalchemy import Boolean, create_engine, Column, String, JSON, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from sqlalchemy.sql import func

load_dotenv()

# Obtener URL de la base de datos desde variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sessions.db")

# Ajustar URL de PostgreSQL si es necesario
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Crear engine sin el parámetro específico de SQLite
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class UserSession(Base):
    __tablename__ = "user_sessions"
    user_id = Column(String, primary_key=True)
    # No longer stores session_data directly

class Chat(Base):
    __tablename__ = "chats"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_sessions.user_id"))
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    token_limit_reached = Column(Boolean, default=False)
    messages = Column(JSON)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()