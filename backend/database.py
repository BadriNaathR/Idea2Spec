"""
Enhanced Database Module with Complete Feature Support
Supports SQLite, PostgreSQL, MySQL, and SQL Server
Now includes: deliverable status, model tracking, token/cost, quality scores, insights, diagrams
"""

import os
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseConfig:
    """Multi-database configuration handler"""
    
    @staticmethod
    def get_connection_string() -> str:
        """Get database connection string based on DB_TYPE environment variable"""
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "sqlite":
            db_file = os.getenv("SQLITE_DB_FILE", "apprelic.db")
            return f"sqlite:///{db_file}"
            
        elif db_type == "postgresql":
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            db = os.getenv("POSTGRES_DB", "apprelic")
            user = os.getenv("POSTGRES_USER", "postgres")
            password = os.getenv("POSTGRES_PASSWORD", "")
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
            
        elif db_type == "mysql":
            host = os.getenv("MYSQL_HOST", "localhost")
            port = os.getenv("MYSQL_PORT", "3306")
            db = os.getenv("MYSQL_DB", "apprelic")
            user = os.getenv("MYSQL_USER", "root")
            password = os.getenv("MYSQL_PASSWORD", "")
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
            
        elif db_type == "mssql":
            host = os.getenv("MSSQL_HOST", "localhost")
            port = os.getenv("MSSQL_PORT", "1433")
            db = os.getenv("MSSQL_DB", "apprelic")
            user = os.getenv("MSSQL_USER", "sa")
            password = os.getenv("MSSQL_PASSWORD", "")
            return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db}?driver=ODBC+Driver+17+for+SQL+Server"
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}")


# Models
class User(Base):
    """User model for BA and Reviewer roles"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # plain text for demo
    role = Column(String(50), nullable=False)  # business_analyst, reviewer
    full_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class DeliverableReview(Base):
    """Review records for deliverables submitted by BA"""
    __tablename__ = "deliverable_reviews"

    id = Column(String(36), primary_key=True)
    analysis_id = Column(String(36), ForeignKey("analysis_results.id"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)  # increments on each resubmit
    checklist = Column(Text)  # BA-provided checklist (JSON array of strings)

    # AI Review (Step 1)
    ai_review_status = Column(String(50), default="pending")  # pending, running, done, failed
    ai_review_result = Column(Text)   # JSON: {sections:[{name,comments,severity,scope_gap}], summary, overall_verdict}
    ai_reviewer_model = Column(String(100))

    # Human Review (Step 2)
    status = Column(String(50), default="submitted")  # submitted, ai_reviewing, pending_human, approved, returned
    human_comments = Column(Text)   # human reviewer's own commentary
    ai_overrides = Column(Text)     # JSON: {section_name: {override_verdict, override_comment}}
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)


class Project(Base):
    """Project model with enhanced metadata"""
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(String(100))
    tags = Column(String(500))
    environment = Column(String(50))
    
    # Source information
    source_type = Column(String(50))  # files, zip, github
    scm_provider = Column(String(50))  # github, gitlab, bitbucket
    scm_repo = Column(String(500))
    scm_branch = Column(String(100))
    
    # Status and metrics
    status = Column(String(50), default="pending")  # pending, processing, ready, error
    file_count = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="project", cascade="all, delete-orphan")
    analyses = relationship("AnalysisResult", back_populates="project", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="project", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    knowledge_base = relationship("KnowledgeBase", back_populates="project", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="project", cascade="all, delete-orphan")
    diagrams = relationship("Diagram", back_populates="project", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Code document chunks for RAG"""
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))
    language = Column(String(50))
    chunk_index = Column(Integer)
    
    # Metadata
    chunk_metadata = Column(JSON)
    embedding_id = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="chunks")


class AnalysisResult(Base):
    """Legacy analysis results table - kept for backward compatibility"""
    __tablename__ = "analysis_results"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    analysis_type = Column(String(100))  # brd, frd, user_stories, test_cases, migration_plan
    model = Column(String(100))  # Model used for analysis
    result = Column(Text)
    status = Column(String(50))
    error_message = Column(Text)
    token_count = Column(Integer)  # Token usage tracking
    cost = Column(Float)  # Cost tracking
    quality_score = Column(Float)  # Quality score
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="analyses")


class Deliverable(Base):
    """Enhanced deliverable model with full status tracking"""
    __tablename__ = "deliverables"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    # Deliverable details
    name = Column(String(255), nullable=False)
    deliverable_type = Column(String(100), nullable=False)  # brd, frd, reverse-eng, tdd, db-analysis, user-stories, test-cases, migration-plan
    description = Column(Text)
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, in-progress, complete, error
    
    # Model and cost tracking
    model_version = Column(String(100))  # gpt-4.1, gpt-4.1-mini, gpt-4o
    token_count = Column(Integer)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    cost = Column(Float)
    
    # Quality metrics
    quality_score = Column(Float)  # 0-100
    completeness_score = Column(Float)  # 0-100
    accuracy_score = Column(Float)  # 0-100
    
    # Content
    content = Column(Text)  # JSON or markdown content
    content_format = Column(String(50))  # json, markdown, html
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_generated_at = Column(DateTime)
    
    # Relationships
    project = relationship("Project", back_populates="deliverables")


class ChatMessage(Base):
    """Enhanced chat messages with mode support"""
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Mode tracking
    mode = Column(String(50))  # code, db, system, general
    
    # Metadata
    chat_metadata = Column(JSON)
    sources = Column(JSON)  # Source files referenced
    token_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="chat_messages")


class KnowledgeBase(Base):
    """Supporting knowledge articles"""
    __tablename__ = "knowledge_base"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    title = Column(String(500))
    content = Column(Text)
    doc_type = Column(String(100))
    priority = Column(Integer, default=0)
    source = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="knowledge_base")


class GitHubIntegration(Base):
    """GitHub integration tracking"""
    __tablename__ = "github_integrations"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    repo_url = Column(String(500))
    branch = Column(String(100))
    access_token = Column(String(500))  # Encrypted in production
    
    last_sync = Column(DateTime)
    sync_status = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Insight(Base):
    """Code insights and recommendations"""
    __tablename__ = "insights"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    # Insight details
    insight_type = Column(String(100))  # code-hotspot, db-optimization, modernization, security, performance
    category = Column(String(100))  # complexity, optimization, architecture, security
    severity = Column(String(50))  # low, medium, high, critical
    
    title = Column(String(500))
    description = Column(Text)
    recommendation = Column(Text)
    impact = Column(Text)
    
    # Metrics
    complexity_score = Column(Float)
    priority_score = Column(Integer)
    
    # Context
    file_path = Column(String(500))
    line_start = Column(Integer)
    line_end = Column(Integer)
    
    # Status
    status = Column(String(50), default="active")  # active, resolved, ignored
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="insights")


class Diagram(Base):
    """Generated diagrams"""
    __tablename__ = "diagrams"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    
    # Diagram details
    diagram_type = Column(String(100))  # architecture, er-diagram, sequence, class, component, wireframe
    title = Column(String(500))
    description = Column(Text)
    
    # Content
    content = Column(Text)  # Mermaid syntax, SVG, or other format
    content_format = Column(String(50))  # mermaid, svg, png, plantuml
    
    # Generation details
    model_version = Column(String(100))
    prompt = Column(Text)
    
    # Status
    status = Column(String(50), default="pending")  # pending, generating, complete, error
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="diagrams")


# Database setup
def get_engine():
    """Get SQLAlchemy engine with connection pooling"""
    connection_string = DatabaseConfig.get_connection_string()
    
    # Connection pool settings
    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    if connection_string.startswith("sqlite"):
        # SQLite doesn't support connection pooling
        engine = create_engine(
            connection_string,
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        engine = create_engine(
            connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False
        )
    
    return engine


def create_tables():
    """Create all database tables"""
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False


def get_session():
    """Get database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with tables"""
    logger.info("Initializing database...")
    db_type = os.getenv("DB_TYPE", "sqlite")
    logger.info(f"Database type: {db_type}")
    
    success = create_tables()
    if success:
        logger.info("✅ Database initialized successfully!")
    else:
        logger.error("❌ Database initialization failed!")
    
    return success


def test_connection():
    """Test database connection"""
    try:
        engine = get_engine()
        with engine.connect() as connection:
            logger.info("✅ Database connection successful!")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test connection
    print("\n🔌 Testing database connection...")
    test_connection()
    
    # Initialize database
    print("\n🏗️ Initializing database...")
    init_db()
    
    print("\n✅ Database setup complete!")
    print(f"Database type: {os.getenv('DB_TYPE', 'sqlite')}")
    print(f"Connection string: {DatabaseConfig.get_connection_string()}")
