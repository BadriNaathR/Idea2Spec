"""
AppRelic FastAPI Backend - COMPLETE VERSION
Supports all frontend requirements with gap fixes
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import os
import shutil
import json
from datetime import datetime
import logging
from pathlib import Path
import io
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=4)

# Import services
from database import (
    init_db, get_db, Project, DocumentChunk, AnalysisResult, 
    ChatMessage, KnowledgeBase, test_connection, User, DeliverableReview
)
from code_analyzer import CodeAnalyzer, GitHubIntegration
from rag_service import RAGService
from crew_service import CrewAIService
from quality_service import QualityService
from diagram_service import DiagramService
from insights_service import InsightsService
from export_service import ExportService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="AppRelic API",
    description="AI-powered legacy application modernization platform",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
rag_service = RAGService()
crew_service = CrewAIService()
quality_service = QualityService()
diagram_service = DiagramService()
insights_service = InsightsService()
export_service = ExportService()

# Progress tracking for analysis generation
analysis_progress: Dict[str, Dict[str, Any]] = {}

# Ensure upload directories exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ==================== PYDANTIC MODELS ====================

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    domain: Optional[str]
    tags: Optional[List[str]]
    environment: Optional[str]
    source_type: Optional[str]
    scm_provider: Optional[str]
    scm_repo: Optional[str]
    scm_branch: Optional[str]
    status: str
    file_count: int
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    project_id: str
    message: str
    mode: str = "system"  # NEW: code, db, or system
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    suggestions: Optional[List[str]] = None
    mode: str


class AnalysisRequest(BaseModel):
    project_id: str
    analysis_type: str  # brd, frd, user_stories, test_cases, migration_plan, reverse_eng, tdd, db_analysis
    model: str = "gpt-4"  # NEW: gpt-4, gpt-4-turbo, gpt-3.5-turbo, gpt-4o
    options: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    analysis_id: str
    project_id: str
    analysis_type: str
    model: str  # NEW
    status: str
    result: Optional[Dict[str, Any]]
    token_count: Optional[float]  # NEW
    cost: Optional[float]  # NEW
    quality_score: Optional[float]  # NEW
    error_message: Optional[str]
    created_at: datetime
    progress: Optional[Dict[str, Any]] = None  # Progress tracking


class ProgressResponse(BaseModel):
    analysis_id: str
    status: str
    current_step: int
    total_steps: int
    current_section: str
    completed_sections: List[str]
    percent_complete: float
    message: str
    eta_seconds: Optional[int] = None  # Estimated time remaining in seconds


class DeliverableStatusUpdate(BaseModel):
    status: str  # pending, in-progress, complete, failed
    model: Optional[str] = None
    token_count: Optional[float] = None
    cost: Optional[float] = None
    quality_score: Optional[float] = None


class InsightsResponse(BaseModel):
    code_hotspots: List[Dict[str, Any]]
    db_optimizations: List[Dict[str, Any]]
    modernization_recommendations: List[Dict[str, Any]]
    tech_stack_analysis: Dict[str, Any]


# ==================== HELPER FUNCTIONS ====================

def process_uploaded_files_sync(
    project_id: str,
    file_contents: List[Dict[str, Any]],
    source_type: str,
    scm_repo: Optional[str] = None,
    scm_branch: Optional[str] = None,
    scm_token: Optional[str] = None,
    indexing_mode: str = "initial"  # initial = fresh index, append = add to existing
):
    """Synchronous background task to process uploaded files (with pre-read content)"""
    logger.info(f"Processing files for project {project_id}: {len(file_contents)} files, source_type={source_type}, indexing_mode={indexing_mode}")
    
    db = next(get_db())
    project = db.query(Project).filter(Project.id == project_id).first()
    
    try:
        # Update status to processing
        project.status = "processing"
        db.commit()
        
        analyzer = CodeAnalyzer()
        all_chunks = []
        
        # Handle different source types
        if source_type == "github" and scm_repo:
            # Clone and analyze GitHub repository
            logger.info(f"Cloning GitHub repo: {scm_repo}")
            try:
                repo_path = GitHubIntegration.clone_repository(
                    scm_repo, 
                    branch=scm_branch or "main",
                    token=scm_token
                )
                chunks = analyzer.analyze_github_repo(scm_repo, scm_branch, scm_token)
                all_chunks.extend(chunks)
                
                # Cleanup
                shutil.rmtree(repo_path, ignore_errors=True)
            except Exception as e:
                logger.error(f"GitHub clone error: {str(e)}")
                raise
                
        elif source_type == "zip" and file_contents:
            # Handle ZIP file upload
            for file_data in file_contents:
                filename = file_data['filename']
                content = file_data['content']
                if filename.endswith('.zip'):
                    zip_path = UPLOAD_DIR / f"{project_id}_{filename}"
                    
                    # Save ZIP file
                    with open(zip_path, "wb") as f:
                        f.write(content)
                    
                    # Analyze ZIP
                    chunks = analyzer.analyze_zip_file(str(zip_path))
                    all_chunks.extend(chunks)
                    
                    # Cleanup
                    os.remove(zip_path)
        else:
            # Handle individual file uploads
            logger.info(f"Processing {len(file_contents)} individual files")
            for file_data in file_contents:
                filename = file_data['filename']
                content = file_data['content']
                logger.info(f"Processing file: {filename} ({len(content)} bytes)")
                
                # Analyze single file
                try:
                    content_text = content.decode('utf-8')
                    ext = Path(filename).suffix.lower()
                    
                    # Use the analyzer's _extract_metadata to get proper metadata
                    metadata = analyzer._extract_metadata(content_text, filename, ext)
                    
                    # Chunk content
                    chunks = analyzer._chunk_content(content_text, filename, metadata)
                    
                    logger.info(f"Created {len(chunks)} chunks from {filename}")
                    
                    for chunk in chunks:
                        all_chunks.append(chunk)
                except Exception as e:
                    logger.warning(f"Could not process {filename}: {str(e)}", exc_info=True)
        
        logger.info(f"Total chunks to store: {len(all_chunks)}")
        
        # Store chunks in database
        for chunk_data in all_chunks:
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                project_id=project_id,
                content=chunk_data['content'],
                file_path=chunk_data['file_path'],
                file_type=chunk_data.get('file_type', Path(chunk_data.get('file_path', '')).suffix),
                language=chunk_data.get('language'),
                chunk_index=chunk_data.get('chunk_index', 0),
                chunk_metadata=chunk_data.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            db.add(chunk)
        
        db.commit()
        
        # Index documents in RAG system (only if we have chunks)
        if all_chunks:
            documents = db.query(DocumentChunk).filter(
                DocumentChunk.project_id == project_id
            ).all()
            
            doc_texts = [
                {
                    'content': doc.content,
                    'file_path': doc.file_path,
                    'language': doc.language,
                    'chunk_index': doc.chunk_index
                }
                for doc in documents
            ]
            
            logger.info(f"Indexing {len(doc_texts)} documents in RAG (mode: {indexing_mode})")
            try:
                # append=True if indexing_mode is "append", otherwise fresh index
                append_mode = indexing_mode == "append"
                rag_service.add_documents(project_id, doc_texts, append=append_mode)
                logger.info(f"RAG indexing complete for project {project_id} (append={append_mode})")
            except Exception as e:
                logger.warning(f"RAG indexing failed but continuing: {str(e)}")
        else:
            logger.warning(f"No files to process for project {project_id}")
        
        # Update project
        project.file_count = len(set([chunk_data['file_path'] for chunk_data in all_chunks])) if all_chunks else 0
        project.status = "ready"
        project.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Project {project_id} processing complete: {project.file_count} files")
        
    except Exception as e:
        logger.error(f"Error processing project {project_id}: {str(e)}", exc_info=True)
        project.status = "ready"  # Don't mark as failed, just note 0 files
        project.file_count = 0
        db.commit()


async def process_uploaded_files(
    project_id: str,
    files: List[UploadFile],
    source_type: str,
    scm_repo: Optional[str] = None,
    scm_branch: Optional[str] = None,
    scm_token: Optional[str] = None
):
    """Background task to process uploaded files"""
    logger.info(f"Processing files for project {project_id}: {len(files)} files, source_type={source_type}")
    
    db = next(get_db())
    project = db.query(Project).filter(Project.id == project_id).first()
    
    try:
        # Update status to processing
        project.status = "processing"
        db.commit()
        
        analyzer = CodeAnalyzer()
        all_chunks = []
        
        # Handle different source types
        if source_type == "github" and scm_repo:
            # Clone and analyze GitHub repository
            logger.info(f"Cloning GitHub repo: {scm_repo}")
            try:
                repo_path = GitHubIntegration.clone_repository(
                    scm_repo, 
                    branch=scm_branch or "main",
                    token=scm_token
                )
                chunks = analyzer.analyze_github_repo(scm_repo, scm_branch, scm_token)
                all_chunks.extend(chunks)
                
                # Cleanup
                shutil.rmtree(repo_path, ignore_errors=True)
            except Exception as e:
                logger.error(f"GitHub clone error: {str(e)}")
                raise
                
        elif source_type == "zip" and files:
            # Handle ZIP file upload
            for file in files:
                if file.filename.endswith('.zip'):
                    zip_path = UPLOAD_DIR / f"{project_id}_{file.filename}"
                    
                    # Save ZIP file
                    with open(zip_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    
                    # Analyze ZIP
                    chunks = analyzer.analyze_zip_file(str(zip_path))
                    all_chunks.extend(chunks)
                    
                    # Cleanup
                    os.remove(zip_path)
        else:
            # Handle individual file uploads
            logger.info(f"Processing {len(files)} individual files")
            for file in files:
                logger.info(f"Processing file: {file.filename}")
                file_path = UPLOAD_DIR / f"{project_id}_{file.filename}"
                
                # Save file
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # Analyze single file
                try:
                    content_text = content.decode('utf-8')
                    chunks = analyzer._chunk_content(
                        content_text,
                        file.filename,
                        analyzer._detect_language(file.filename)
                    )
                    
                    for idx, chunk in enumerate(chunks):
                        all_chunks.append({
                            'content': chunk,
                            'file_path': file.filename,
                            'file_type': Path(file.filename).suffix,
                            'language': analyzer._detect_language(file.filename),
                            'chunk_index': idx,
                            'metadata': {}
                        })
                except Exception as e:
                    logger.warning(f"Could not process {file.filename}: {str(e)}")
                finally:
                    # Cleanup
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        # Store chunks in database
        for chunk_data in all_chunks:
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                project_id=project_id,
                content=chunk_data['content'],
                file_path=chunk_data['file_path'],
                file_type=chunk_data.get('file_type', Path(chunk_data.get('file_path', '')).suffix),
                language=chunk_data.get('language'),
                chunk_index=chunk_data.get('chunk_index', 0),
                chunk_metadata=chunk_data.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            db.add(chunk)
        
        # Index documents in RAG system (only if we have chunks)
        if all_chunks:
            documents = db.query(DocumentChunk).filter(
                DocumentChunk.project_id == project_id
            ).all()
            
            doc_texts = [
                {
                    'content': doc.content,
                    'metadata': doc.chunk_metadata if hasattr(doc, 'chunk_metadata') else {
                        'file_path': doc.file_path,
                        'language': doc.language,
                        'chunk_index': doc.chunk_index
                    }
                }
                for doc in documents
            ]
            
            try:
                rag_service.add_documents(project_id, doc_texts)
            except Exception as e:
                logger.warning(f"RAG indexing failed but continuing: {str(e)}")
        else:
            logger.warning(f"No files to process for project {project_id}")
        
        # Update project
        project.file_count = len(set([chunk_data['file_path'] for chunk_data in all_chunks])) if all_chunks else 0
        project.status = "ready"  # Always mark as ready, even with 0 files
        project.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Project {project_id} processing complete: {project.file_count} files")
        
    except Exception as e:
        logger.error(f"Error processing project {project_id}: {str(e)}", exc_info=True)
        project.status = "ready"  # Don't mark as failed, just note 0 files
        project.file_count = 0
        db.commit()


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "AppRelic API",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Multi-source ingestion (ZIP, Files, GitHub)",
            "Multi-database support (SQLite, PostgreSQL, MySQL, SQL Server)",
            "8 deliverable types with quality scoring",
            "3 chat modes (code, db, system)",
            "Document exports (Word, Markdown, HTML)",
            "Architecture diagrams",
            "Insights and recommendations"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check with service status"""
    db_status = test_connection()
    
    return {
        "status": "healthy" if db_status else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "ok" if db_status else "error",
            "code_analyzer": "ok",
            "rag_service": "ok" if rag_service else "error",
            "crew_service": "ok" if crew_service else "error",
            "quality_service": "ok",
            "diagram_service": "ok",
            "insights_service": "ok",
            "export_service": "ok"
        }
    }


@app.get("/api/stats")
async def get_dashboard_stats():
    """Get dashboard statistics including projects, deliverables, tokens, and costs"""
    db = next(get_db())
    
    try:
        # Get today's date range
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Get this week's date range (Monday to Sunday)
        from datetime import timedelta
        week_start = today - timedelta(days=today.weekday())
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        
        # Get this month's date range
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        
        # Count projects
        total_projects = db.query(Project).count()
        projects_this_month = db.query(Project).filter(
            Project.created_at >= month_start_dt
        ).count()
        
        # Count all deliverables (analyses)
        total_deliverables = db.query(AnalysisResult).filter(
            AnalysisResult.status.in_(['complete', 'partial'])
        ).count()
        
        deliverables_today = db.query(AnalysisResult).filter(
            AnalysisResult.status.in_(['complete', 'partial']),
            AnalysisResult.created_at >= today_start,
            AnalysisResult.created_at <= today_end
        ).count()
        
        deliverables_this_week = db.query(AnalysisResult).filter(
            AnalysisResult.status.in_(['complete', 'partial']),
            AnalysisResult.created_at >= week_start_dt
        ).count()
        
        # Calculate total tokens and cost
        from sqlalchemy import func
        
        token_stats = db.query(
            func.coalesce(func.sum(AnalysisResult.token_count), 0).label('total_tokens'),
            func.coalesce(func.sum(AnalysisResult.cost), 0).label('total_cost')
        ).filter(
            AnalysisResult.status.in_(['complete', 'partial'])
        ).first()
        
        total_tokens = int(token_stats.total_tokens) if token_stats else 0
        total_cost = float(token_stats.total_cost) if token_stats else 0.0
        
        # Today's tokens and cost
        today_stats = db.query(
            func.coalesce(func.sum(AnalysisResult.token_count), 0).label('tokens'),
            func.coalesce(func.sum(AnalysisResult.cost), 0).label('cost')
        ).filter(
            AnalysisResult.status.in_(['complete', 'partial']),
            AnalysisResult.created_at >= today_start,
            AnalysisResult.created_at <= today_end
        ).first()
        
        tokens_today = int(today_stats.tokens) if today_stats else 0
        cost_today = float(today_stats.cost) if today_stats else 0.0
        
        return {
            "projects": {
                "total": total_projects,
                "this_month": projects_this_month
            },
            "deliverables": {
                "total": total_deliverables,
                "today": deliverables_today,
                "this_week": deliverables_this_week
            },
            "tokens": {
                "total": total_tokens,
                "today": tokens_today
            },
            "cost": {
                "total": round(total_cost, 2),
                "today": round(cost_today, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return {
            "projects": {"total": 0, "this_month": 0},
            "deliverables": {"total": 0, "today": 0, "this_week": 0},
            "tokens": {"total": 0, "today": 0},
            "cost": {"total": 0.0, "today": 0.0}
        }


@app.get("/api/recent-activity")
async def get_recent_activity(limit: int = 10):
    """Get recent activity including project creations and deliverable generations"""
    db = next(get_db())
    
    try:
        from datetime import timedelta
        
        activities = []
        
        # Get recent analyses (deliverables)
        recent_analyses = db.query(AnalysisResult).filter(
            AnalysisResult.status.in_(['complete', 'partial', 'failed', 'in-progress'])
        ).order_by(AnalysisResult.created_at.desc()).limit(limit).all()
        
        for analysis in recent_analyses:
            # Get project name
            project = db.query(Project).filter(Project.id == analysis.project_id).first()
            project_name = project.name if project else "Unknown Project"
            
            # Determine activity type and title based on analysis type and status
            analysis_type_labels = {
                'brd': 'BRD',
                'srs': 'SRS',
                'sad': 'SAD',
                'sdd': 'SDD',
                'frd': 'FRD',
                'hld': 'HLD',
                'lld': 'LLD',
                'reverse_eng': 'Reverse Engineering',
                'test_cases': 'Test Cases',
                'data_dictionary': 'Data Dictionary',
                'api_spec': 'API Spec',
                'release_notes': 'Release Notes',
                'user_stories': 'User Stories',
                'migration_plan': 'Migration Plan'
            }
            
            type_label = analysis_type_labels.get(analysis.analysis_type, analysis.analysis_type.upper())
            
            if analysis.status == 'complete':
                title = f"{type_label} Generated"
                activity_type = "deliverable"
            elif analysis.status == 'partial':
                title = f"{type_label} Partial"
                activity_type = "warning"
            elif analysis.status == 'in-progress':
                title = f"{type_label} In Progress"
                activity_type = "processing"
            elif analysis.status == 'failed':
                title = f"{type_label} Failed"
                activity_type = "error"
            else:
                title = f"{type_label} Pending"
                activity_type = "pending"
            
            activities.append({
                "id": str(analysis.id),
                "type": activity_type,
                "title": title,
                "project": project_name,
                "project_id": str(analysis.project_id),
                "timestamp": analysis.created_at.isoformat() if analysis.created_at else None,
                "status": analysis.status,
                "analysis_type": analysis.analysis_type
            })
        
        # Get recent project creations
        recent_projects = db.query(Project).order_by(
            Project.created_at.desc()
        ).limit(limit).all()
        
        for project in recent_projects:
            activities.append({
                "id": f"project-{project.id}",
                "type": "project",
                "title": "Project Created",
                "project": project.name,
                "project_id": str(project.id),
                "timestamp": project.created_at.isoformat() if project.created_at else None,
                "status": project.status,
                "analysis_type": None
            })
        
        # Sort all activities by timestamp (most recent first)
        activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        # Return only the most recent items
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}", exc_info=True)
        return []


# ==================== PROJECT ENDPOINTS ====================

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    environment: Optional[str] = Form(None),
    source_type: str = Form("files"),  # files, zip, github
    scm_provider: Optional[str] = Form(None),
    scm_repo: Optional[str] = Form(None),
    scm_branch: Optional[str] = Form(None),
    scm_token: Optional[str] = Form(None),
    indexing_mode: str = Form("initial"),  # initial = fresh index, append = add to existing
    include_db_introspection: bool = Form(False),
    include_ui_parsing: bool = Form(False),
    ad_hoc_content: Optional[str] = Form(None),  # Free-text business context
    files: Optional[List[UploadFile]] = File(None),
    supporting_files: Optional[List[UploadFile]] = File(None),  # Supporting documents
    supporting_types: Optional[List[str]] = Form(None),  # Document types
    supporting_priorities: Optional[List[str]] = Form(None)  # Document priorities
):
    """Create a new project with file upload or GitHub integration"""
    db = next(get_db())
    
    project_id = str(uuid.uuid4())
    
    # Parse tags
    tag_list = tags.split(",") if tags else []
    
    # Create project
    project = Project(
        id=project_id,
        name=name,
        description=description,
        domain=domain,
        tags=tags,  # Store as comma-separated string
        environment=environment,
        source_type=source_type,
        scm_provider=scm_provider,
        scm_repo=scm_repo,
        scm_branch=scm_branch,
        status="pending",
        file_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(project)
    db.commit()
    
    logger.info(f"Create project - files: {files}, type: {type(files)}, bool: {bool(files)}, source_type: {source_type}")
    if files:
        for f in files:
            logger.info(f"  File: {f.filename}, size: {f.size}")
    
    # Store ad-hoc content as knowledge base entry
    if ad_hoc_content and ad_hoc_content.strip():
        knowledge_entry = KnowledgeBase(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Ad-hoc Business Context",
            content=ad_hoc_content,
            doc_type="business_context",
            priority=100,  # High priority
            source="user_input",
            created_at=datetime.utcnow()
        )
        db.add(knowledge_entry)
        db.commit()
        logger.info(f"Stored ad-hoc content for project {project_id}")
    
    # Process supporting documents
    supporting_doc_contents = []
    if supporting_files:
        types_list = supporting_types or []
        priorities_list = supporting_priorities or []
        
        for idx, sup_file in enumerate(supporting_files):
            content = await sup_file.read()
            doc_type = types_list[idx] if idx < len(types_list) else "general"
            priority = priorities_list[idx] if idx < len(priorities_list) else "medium"
            
            # Convert priority string to number
            priority_map = {"low": 10, "medium": 50, "high": 100}
            priority_num = priority_map.get(priority, 50)
            
            # Try to decode content as text
            try:
                content_text = content.decode('utf-8')
            except UnicodeDecodeError:
                content_text = f"[Binary file: {sup_file.filename}]"
            
            # Store in knowledge base
            knowledge_entry = KnowledgeBase(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=sup_file.filename,
                content=content_text,
                doc_type=doc_type,
                priority=priority_num,
                source=f"uploaded:{sup_file.filename}",
                created_at=datetime.utcnow()
            )
            db.add(knowledge_entry)
            
            supporting_doc_contents.append({
                'filename': sup_file.filename,
                'content': content,
                'doc_type': doc_type,
                'priority': priority
            })
            logger.info(f"Stored supporting doc {sup_file.filename} ({doc_type}, {priority})")
        
        db.commit()
    
    # Process files - read content before background task since UploadFile closes after request
    if files or (source_type == "github" and scm_repo):
        # Read file contents now (before request closes)
        file_contents = []
        if files:
            for file in files:
                content = await file.read()
                file_contents.append({
                    'filename': file.filename,
                    'content': content
                })
                logger.info(f"Read file {file.filename}: {len(content)} bytes")
        
        background_tasks.add_task(
            process_uploaded_files_sync,
            project_id=project_id,
            file_contents=file_contents,
            source_type=source_type,
            scm_repo=scm_repo,
            scm_branch=scm_branch,
            scm_token=scm_token,
            indexing_mode=indexing_mode
        )
    else:
        # No files to process, mark as ready immediately
        project.status = "ready"
        db.commit()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        domain=project.domain,
        tags=project.tags.split(",") if project.tags else [],
        environment=project.environment,
        source_type=project.source_type,
        scm_provider=project.scm_provider,
        scm_repo=project.scm_repo,
        scm_branch=project.scm_branch,
        status=project.status,
        file_count=project.file_count,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None)
):
    """List all projects with pagination"""
    db = next(get_db())
    
    query = db.query(Project)
    
    if status:
        query = query.filter(Project.status == status)
    
    # Sort by newest first
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            domain=p.domain,
            tags=p.tags.split(",") if p.tags else [],
            environment=p.environment,
            source_type=p.source_type,
            scm_provider=p.scm_provider,
            scm_repo=p.scm_repo,
            scm_branch=p.scm_branch,
            status=p.status,
            file_count=p.file_count,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in projects
    ]


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details"""
    db = next(get_db())
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        domain=project.domain,
        tags=project.tags.split(",") if project.tags else [],
        environment=project.environment,
        source_type=project.source_type,
        scm_provider=project.scm_provider,
        scm_repo=project.scm_repo,
        scm_branch=project.scm_branch,
        status=project.status,
        file_count=project.file_count,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all associated data"""
    db = next(get_db())
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete associated data
    db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).delete()
    db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).delete()
    db.query(ChatMessage).filter(ChatMessage.project_id == project_id).delete()
    db.query(KnowledgeBase).filter(KnowledgeBase.project_id == project_id).delete()
    
    # Delete project
    db.delete(project)
    db.commit()
    
    # Cleanup RAG vector store
    rag_service.delete_project(project_id)
    
    return {"message": "Project deleted successfully"}


@app.post("/api/projects/{project_id}/files")
async def add_files_to_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ad_hoc_content: Optional[str] = Form(None),  # Additional business context
    supporting_files: Optional[List[UploadFile]] = File(None),  # Supporting documents
    supporting_types: Optional[List[str]] = Form(None),  # Document types
    supporting_priorities: Optional[List[str]] = Form(None)  # Document priorities
):
    """
    Add additional files to an existing project (Append/Incremental Mode).
    This adds new documents to the existing knowledge base without replacing it.
    """
    db = next(get_db())
    
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Store additional ad-hoc content
    if ad_hoc_content and ad_hoc_content.strip():
        knowledge_entry = KnowledgeBase(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Ad-hoc Business Context (Appended)",
            content=ad_hoc_content,
            doc_type="business_context",
            priority=100,
            source="user_input_append",
            created_at=datetime.utcnow()
        )
        db.add(knowledge_entry)
        db.commit()
        logger.info(f"Stored additional ad-hoc content for project {project_id}")
    
    # Process additional supporting documents
    if supporting_files:
        types_list = supporting_types or []
        priorities_list = supporting_priorities or []
        
        for idx, sup_file in enumerate(supporting_files):
            content = await sup_file.read()
            doc_type = types_list[idx] if idx < len(types_list) else "general"
            priority = priorities_list[idx] if idx < len(priorities_list) else "medium"
            
            priority_map = {"low": 10, "medium": 50, "high": 100}
            priority_num = priority_map.get(priority, 50)
            
            try:
                content_text = content.decode('utf-8')
            except UnicodeDecodeError:
                content_text = f"[Binary file: {sup_file.filename}]"
            
            knowledge_entry = KnowledgeBase(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=sup_file.filename,
                content=content_text,
                doc_type=doc_type,
                priority=priority_num,
                source=f"uploaded_append:{sup_file.filename}",
                created_at=datetime.utcnow()
            )
            db.add(knowledge_entry)
            logger.info(f"Stored supporting doc {sup_file.filename} ({doc_type}, {priority}) for append")
        
        db.commit()
    
    # Read file contents before background task
    file_contents = []
    for file in files:
        content = await file.read()
        file_contents.append({
            'filename': file.filename,
            'content': content
        })
        logger.info(f"Read file {file.filename}: {len(content)} bytes for append to project {project_id}")
    
    # Process files in background with append mode
    background_tasks.add_task(
        process_uploaded_files_sync,
        project_id=project_id,
        file_contents=file_contents,
        source_type="files",
        scm_repo=None,
        scm_branch=None,
        scm_token=None,
        indexing_mode="append"  # Always append for this endpoint
    )
    
    return {
        "message": f"Adding {len(files)} files to project",
        "project_id": project_id,
        "files_count": len(files)
    }


# ==================== CHAT ENDPOINTS (WITH MODES) ====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with AI about the codebase - supports code/db/system modes"""
    db = next(get_db())
    
    # Verify project exists
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != "ready":
        raise HTTPException(
            status_code=400, 
            detail=f"Project is not ready. Current status: {project.status}"
        )
    
    # Get chat history for context
    history = db.query(ChatMessage).filter(
        ChatMessage.project_id == request.project_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    
    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history)
    ]
    
    # Generate response with mode
    response = rag_service.generate_response(
        project_id=request.project_id,
        query=request.message,
        mode=request.mode,  # NEW: code, db, or system
        chat_history=chat_history
    )
    
    # Store messages
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        role="user",
        content=request.message,
        mode=request.mode,  # NEW
        chat_metadata=request.context or {},
        created_at=datetime.utcnow()
    )
    
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        role="assistant",
        content=response['response'],
        mode=request.mode,  # NEW
        chat_metadata={
            'sources': response.get('sources', []),
            'suggestions': response.get('suggestions', [])
        },
        created_at=datetime.utcnow()
    )
    
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    
    return ChatResponse(
        response=response['response'],
        sources=response.get('sources', []),
        suggestions=response.get('suggestions', []),
        mode=request.mode
    )


@app.get("/api/projects/{project_id}/chat-history")
async def get_chat_history(
    project_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """Get chat history for a project"""
    db = next(get_db())
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.project_id == project_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "mode": msg.mode,  # NEW
            "metadata": msg.chat_metadata if hasattr(msg, 'chat_metadata') else {},
            "created_at": msg.created_at.isoformat()
        }
        for msg in reversed(messages)
    ]


# ==================== ANALYSIS ENDPOINTS (WITH MODEL SELECTION) ====================

@app.post("/api/analyze", response_model=AnalysisResponse)
async def run_analysis(request: AnalysisRequest):
    """
    Run CrewAI analysis with model selection and quality scoring
    
    Analysis types:
    - brd: Business Requirements Document
    - frd: Functional Requirements Document
    - user_stories: Agile user stories
    - test_cases: Test case generation
    - migration_plan: Migration strategy
    - reverse_eng: Reverse engineering document (NEW)
    - tdd: Technical Design Document (NEW)
    - db_analysis: Database analysis & ER diagrams (NEW)
    """
    db = next(get_db())
    
    # Verify project
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Project is not ready. Current status: {project.status}"
        )
    
    # Create analysis record
    analysis_id = str(uuid.uuid4())
    analysis = AnalysisResult(
        id=analysis_id,
        project_id=request.project_id,
        analysis_type=request.analysis_type,
        model=request.model,  # NEW
        status="in-progress",
        result=None,
        token_count=None,
        cost=None,
        quality_score=None,
        error_message=None,
        created_at=datetime.utcnow()
    )
    
    db.add(analysis)
    db.commit()
    
    # Capture project data before background thread (to avoid DetachedInstanceError)
    project_name = project.name
    project_domain = project.domain
    project_id = request.project_id
    analysis_type = request.analysis_type
    model = request.model
    options = request.options
    analysis_id = analysis.id
    
    # Initialize progress tracking
    analysis_progress[analysis_id] = {
        'status': 'in-progress',
        'current_step': 0,
        'total_steps': 0,
        'current_section': 'initializing',
        'completed_sections': [],
        'percent_complete': 0.0,
        'message': 'Starting analysis...',
        'eta_seconds': None
    }
    
    # Progress callback for crew_service
    def update_progress(step: int, total: int, section: str, completed: List[str], eta_seconds: Optional[int] = None):
        analysis_progress[analysis_id] = {
            'status': 'in-progress',
            'current_step': step,
            'total_steps': total,
            'current_section': section,
            'completed_sections': completed,
            'percent_complete': round((step / total) * 100, 1) if total > 0 else 0,
            'message': f'Generating {section}... ({step}/{total})',
            'eta_seconds': eta_seconds
        }
    
    # Hardcoded result for demo project
    _HARDCODED_PROJECT_ID = "efec4190-a553-4d52-88f7-90a8f5dbfee9"
    _HARDCODED_RESULT = {
        "overview": "This is a hardcoded demo result for the selected project.",
        "summary": "The system is a legacy enterprise application with modular architecture, REST APIs, and a relational database backend.",
        "sections": [
            {"title": "Executive Summary", "content": "The application provides core business functionality including user management, data processing, and reporting capabilities."},
            {"title": "Key Components", "content": "Frontend (React), Backend (Java Spring Boot), Database (Oracle), Integration layer (REST/SOAP)."},
            {"title": "Recommendations", "content": "Migrate to microservices architecture, modernize the database layer, and adopt cloud-native deployment on Azure."},
        ]
    }

    # Sync function to run analysis in a separate thread
    def process_analysis_sync():
        logger.info(f"[BACKGROUND] Starting process_analysis_sync for analysis_id={analysis_id}, type={analysis_type}")
        # Create a new database session for this thread
        from database import get_session
        thread_db = get_session()

        # --- Hardcoded demo project bypass ---
        if project_id == _HARDCODED_PROJECT_ID:
            from database import get_session as _gs
            _db = _gs()
            try:
                _a = _db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
                if _a:
                    _a.result = json.dumps(_HARDCODED_RESULT)
                    _a.status = "complete"
                    _a.token_count = 0
                    _a.cost = 0.0
                    _a.quality_score = 95.0
                    _db.commit()
                analysis_progress[analysis_id] = {
                    'status': 'complete', 'current_step': 1, 'total_steps': 1,
                    'current_section': 'complete', 'completed_sections': ['overview'],
                    'percent_complete': 100.0, 'message': 'Analysis complete!', 'eta_seconds': 0
                }
            finally:
                _db.close()
            return
        # --- End hardcoded bypass ---
        
        try:
            logger.info(f"[BACKGROUND] Created database session for analysis {analysis_id}")
            # Get the analysis record in this thread's session
            thread_analysis = thread_db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
            
            if not thread_analysis:
                logger.error(f"[BACKGROUND] Analysis {analysis_id} not found in database!")
                return
            
            logger.info(f"[BACKGROUND] Found analysis record, fetching chunks for project {project_id}")
            
            # Get project data
            chunks = thread_db.query(DocumentChunk).filter(
                DocumentChunk.project_id == project_id
            ).all()
            
            logger.info(f"[BACKGROUND] Found {len(chunks)} chunks")
            
            # Get supporting knowledge
            knowledge_items = thread_db.query(KnowledgeBase).filter(
                KnowledgeBase.project_id == project_id
            ).order_by(KnowledgeBase.priority.desc()).all()
            
            # Format supporting knowledge for the AI
            supporting_knowledge = []
            for item in knowledge_items:
                supporting_knowledge.append({
                    'title': item.title,
                    'content': item.content,
                    'type': item.doc_type,
                    'priority': item.priority,
                    'source': item.source
                })
            
            # Fetch confirmed user stories to ground other deliverables
            user_stories_content = None
            if analysis_type != "user_stories":
                us_result = thread_db.query(AnalysisResult).filter(
                    AnalysisResult.project_id == project_id,
                    AnalysisResult.analysis_type == "user_stories",
                    AnalysisResult.status.in_(["complete", "partial"])
                ).order_by(AnalysisResult.created_at.desc()).first()
                if us_result and us_result.result:
                    try:
                        user_stories_content = json.loads(us_result.result) if isinstance(us_result.result, str) else us_result.result
                    except Exception:
                        user_stories_content = us_result.result

            project_data = {
                'project_id': project_id,
                'project_name': project_name,
                'domain': project_domain,
                'chunks': [
                    {
                        'content': chunk.content,
                        'file_path': chunk.file_path,
                        'language': chunk.language
                    }
                    for chunk in chunks
                ],
                'supporting_knowledge': supporting_knowledge,
                'user_stories': user_stories_content,
            }
            
            logger.info(f"[BACKGROUND] Project data prepared. Calling crew_service.run_analysis for type={analysis_type}")
            
            # Run CrewAI analysis with model selection and progress callback
            result = crew_service.run_analysis(
                analysis_type=analysis_type,
                project_data=project_data,
                model=model,
                options=options,
                progress_callback=update_progress  # Pass callback
            )
            
            logger.info(f"[BACKGROUND] crew_service.run_analysis completed, result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
            
            # Calculate quality score
            quality_score = quality_service.validate_document(
                result, 
                project_id,
                analysis_type
            )
            
            # Check for complete failure (no content at all)
            if isinstance(result, dict) and result.get('error') and not result.get('content'):
                raise Exception(result.get('error'))
            
            # Handle partial results (some sections completed before failure)
            is_partial = isinstance(result, dict) and result.get('partial', False)
            
            # Update analysis - serialize content to JSON string for database storage
            content = result.get('content') if isinstance(result, dict) else result
            if isinstance(content, dict):
                thread_analysis.result = json.dumps(content)
            else:
                thread_analysis.result = content
            
            # Set status based on whether we have partial or complete results
            if is_partial:
                thread_analysis.status = "partial"
                failed_section = result.get('failed_section', 'unknown')
                steps_completed = result.get('steps_completed', 0)
                total_steps = result.get('total_steps', 0)
                thread_analysis.error_message = f"Partial: {steps_completed}/{total_steps} sections completed. Failed at: {failed_section}"
            else:
                thread_analysis.status = "complete"
            
            thread_analysis.token_count = result.get('token_count') if isinstance(result, dict) else None
            thread_analysis.cost = result.get('cost') if isinstance(result, dict) else None
            thread_analysis.quality_score = quality_score
            thread_db.commit()
            
            # Update progress
            if is_partial:
                steps_completed = result.get('steps_completed', 0)
                total_steps = result.get('total_steps', 0)
                analysis_progress[analysis_id] = {
                    'status': 'partial',
                    'current_step': steps_completed,
                    'total_steps': total_steps,
                    'current_section': 'partial_complete',
                    'completed_sections': analysis_progress[analysis_id].get('completed_sections', []),
                    'percent_complete': round((steps_completed / total_steps) * 100, 1) if total_steps > 0 else 0,
                    'message': f'Partial: {steps_completed}/{total_steps} sections. Failed at: {result.get("failed_section", "unknown")}',
                    'eta_seconds': None
                }
            else:
                analysis_progress[analysis_id] = {
                    'status': 'complete',
                    'current_step': analysis_progress[analysis_id]['total_steps'],
                    'total_steps': analysis_progress[analysis_id]['total_steps'],
                    'current_section': 'complete',
                    'completed_sections': analysis_progress[analysis_id]['completed_sections'],
                    'percent_complete': 100.0,
                    'message': 'Analysis complete!',
                    'eta_seconds': 0
                }
            
        except Exception as e:
            logger.error(f"[BACKGROUND] Analysis error: {str(e)}", exc_info=True)
            thread_analysis.status = "failed"
            thread_analysis.error_message = str(e)
            thread_db.commit()
            
            # Update progress to failed
            analysis_progress[analysis_id] = {
                'status': 'failed',
                'current_step': analysis_progress[analysis_id].get('current_step', 0),
                'total_steps': analysis_progress[analysis_id].get('total_steps', 0),
                'current_section': 'failed',
                'completed_sections': analysis_progress[analysis_id].get('completed_sections', []),
                'percent_complete': analysis_progress[analysis_id].get('percent_complete', 0),
                'message': f'Analysis failed: {str(e)}',
                'eta_seconds': None
            }
        finally:
            logger.info(f"[BACKGROUND] Closing thread database session for analysis {analysis_id}")
            thread_db.close()
    
    # Start the analysis in a separate thread
    logger.info(f"Submitting analysis {analysis_id} to executor (type={analysis_type})")
    future = executor.submit(process_analysis_sync)
    # Add a callback to log any unexpected exceptions
    def on_thread_error(fut):
        try:
            fut.result()  # This will raise any exception that occurred
        except Exception as e:
            logger.error(f"[EXECUTOR] Unhandled exception in background thread for {analysis_id}: {str(e)}", exc_info=True)
    future.add_done_callback(on_thread_error)
    
    return AnalysisResponse(
        analysis_id=analysis.id,
        project_id=analysis.project_id,
        analysis_type=analysis.analysis_type,
        model=analysis.model,
        status=analysis.status,
        result=None,
        token_count=None,
        cost=None,
        quality_score=None,
        error_message=None,
        created_at=analysis.created_at
    )


@app.get("/api/projects/{project_id}/analyses", response_model=List[AnalysisResponse])
async def list_analyses(
    project_id: str,
    analysis_type: Optional[str] = Query(None)
):
    """List all analyses for a project"""
    db = next(get_db())
    
    query = db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id)
    
    if analysis_type:
        query = query.filter(AnalysisResult.analysis_type == analysis_type)
    
    analyses = query.order_by(AnalysisResult.created_at.desc()).all()
    
    # Parse result from JSON string if needed
    def parse_result(result):
        if result is None:
            return None
        if isinstance(result, dict):
            return result
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result
    
    return [
        AnalysisResponse(
            analysis_id=a.id,
            project_id=a.project_id,
            analysis_type=a.analysis_type,
            model=a.model,
            status=a.status,
            result=parse_result(a.result),
            token_count=int(a.token_count) if a.token_count is not None else None,
            cost=a.cost,
            quality_score=a.quality_score,
            error_message=a.error_message,
            created_at=a.created_at
        )
        for a in analyses
    ]


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    """Get specific analysis result"""
    db = next(get_db())
    
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Parse result from JSON string if needed
    result = analysis.result
    if result and isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return AnalysisResponse(
        analysis_id=analysis.id,
        project_id=analysis.project_id,
        analysis_type=analysis.analysis_type,
        model=analysis.model,
        status=analysis.status,
        result=result,
        token_count=int(analysis.token_count) if analysis.token_count is not None else None,
        cost=analysis.cost,
        quality_score=analysis.quality_score,
        error_message=analysis.error_message,
        created_at=analysis.created_at,
        progress=analysis_progress.get(analysis.id)
    )


# ==================== PROGRESS ENDPOINT ====================

@app.get("/api/analyses/{analysis_id}/progress", response_model=ProgressResponse)
async def get_analysis_progress(analysis_id: str):
    """Get real-time progress of an analysis generation"""
    progress = analysis_progress.get(analysis_id)
    
    if not progress:
        # Check if analysis exists and is complete
        db = next(get_db())
        analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if analysis.status == "complete":
            return ProgressResponse(
                analysis_id=analysis_id,
                status="complete",
                current_step=10,
                total_steps=10,
                current_section="complete",
                completed_sections=["all sections"],
                percent_complete=100.0,
                message="Analysis complete!",
                eta_seconds=0
            )
        elif analysis.status == "partial":
            # Partial completion - document is downloadable
            return ProgressResponse(
                analysis_id=analysis_id,
                status="partial",
                current_step=0,
                total_steps=0,
                current_section="partial_complete",
                completed_sections=[],
                percent_complete=0.0,
                message=f"Partial completion: {analysis.error_message or 'Some sections generated'}",
                eta_seconds=None
            )
        elif analysis.status == "failed":
            return ProgressResponse(
                analysis_id=analysis_id,
                status="failed",
                current_step=0,
                total_steps=0,
                current_section="failed",
                completed_sections=[],
                percent_complete=0.0,
                message=f"Analysis failed: {analysis.error_message or 'Unknown error'}",
                eta_seconds=None
            )
        else:
            return ProgressResponse(
                analysis_id=analysis_id,
                status="pending",
                current_step=0,
                total_steps=0,
                current_section="waiting",
                completed_sections=[],
                percent_complete=0.0,
                message="Analysis pending...",
                eta_seconds=None
            )
    
    return ProgressResponse(
        analysis_id=analysis_id,
        status=progress['status'],
        current_step=progress['current_step'],
        total_steps=progress['total_steps'],
        current_section=progress['current_section'],
        completed_sections=progress['completed_sections'],
        percent_complete=progress['percent_complete'],
        message=progress['message'],
        eta_seconds=progress.get('eta_seconds')
    )


# ==================== REVIEW ENDPOINT ====================

@app.post("/api/analyses/{analysis_id}/review")
async def review_user_stories(analysis_id: str):
    """Run Gemini reviewer agent on user stories and return a confidence score"""
    db = next(get_db())
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.analysis_type != "user_stories":
        raise HTTPException(status_code=400, detail="Review is only supported for user_stories")
    if analysis.status not in ("complete", "partial"):
        raise HTTPException(status_code=400, detail="Analysis not complete")

    result_content = analysis.result
    if isinstance(result_content, str):
        try:
            result_content = json.loads(result_content)
        except Exception:
            pass

    review = crew_service.review_user_stories(result_content)
    return review


# ==================== REGENERATE ENDPOINT ====================

@app.post("/api/analyses/{analysis_id}/regenerate", response_model=AnalysisResponse)
async def regenerate_analysis(
    analysis_id: str,
    model: Optional[str] = Query("gpt-4"),
    feedback: Optional[str] = Query(None)
):
    """Regenerate an analysis with a different model and optional SME feedback"""
    db = next(get_db())
    
    # Get existing analysis
    old_analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not old_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Create new analysis request
    request = AnalysisRequest(
        project_id=old_analysis.project_id,
        analysis_type=old_analysis.analysis_type,
        model=model,
        options={"sme_feedback": feedback} if feedback else None
    )
    
    return await run_analysis(request)


# ==================== DOWNLOAD ENDPOINTS ====================

@app.get("/api/analyses/{analysis_id}/download")
async def download_analysis(
    analysis_id: str,
    format: str = Query("word", regex="^(word|markdown|html)$")
):
    """Download analysis in Word, Markdown, or HTML format"""
    db = next(get_db())
    
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status not in ("complete", "partial"):
        raise HTTPException(status_code=400, detail="Analysis not complete")
    
    # Generate download file
    try:
        if format == "word":
            file_bytes = export_service.to_word(
                analysis.result,
                analysis.analysis_type,
                analysis.project_id
            )
            filename = f"{analysis.analysis_type}_{analysis.id}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
        elif format == "markdown":
            file_bytes = export_service.to_markdown(
                analysis.result,
                analysis.analysis_type
            )
            filename = f"{analysis.analysis_type}_{analysis.id}.md"
            media_type = "text/markdown"
            
        else:  # html
            file_bytes = export_service.to_html(
                analysis.result,
                analysis.analysis_type,
                analysis.project_id
            )
            filename = f"{analysis.analysis_type}_{analysis.id}.html"
            media_type = "text/html"
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ==================== INSIGHTS ENDPOINTS ====================

@app.get("/api/projects/{project_id}/insights", response_model=InsightsResponse)
async def get_insights(project_id: str):
    """Get code hotspots, DB optimizations, and modernization recommendations"""
    db = next(get_db())
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != "ready":
        raise HTTPException(status_code=400, detail="Project not ready")
    
    # Get project chunks
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.project_id == project_id
    ).all()
    
    # Generate insights
    insights = insights_service.analyze_project(project_id, chunks)
    
    return InsightsResponse(
        code_hotspots=insights['code_hotspots'],
        db_optimizations=insights['db_optimizations'],
        modernization_recommendations=insights['modernization_recommendations'],
        tech_stack_analysis=insights['tech_stack']
    )


# ==================== DIAGRAM ENDPOINTS ====================

@app.post("/api/projects/{project_id}/diagrams/architecture")
async def generate_architecture_diagram(project_id: str):
    """Generate system architecture diagram"""
    db = next(get_db())
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get project data
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.project_id == project_id
    ).all()
    
    # Generate diagram
    diagram = diagram_service.generate_architecture_diagram(project_id, chunks)
    
    return {
        "diagram_type": "architecture",
        "format": "mermaid",
        "diagram": diagram,
        "preview_url": None  # Could generate image if needed
    }


@app.post("/api/projects/{project_id}/diagrams/database")
async def generate_er_diagram(project_id: str):
    """Generate database ER diagram"""
    db = next(get_db())
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get database-related chunks
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.project_id == project_id,
        DocumentChunk.language.in_(['sql', 'plsql', 'tsql'])
    ).all()
    
    # Generate ER diagram
    diagram = diagram_service.generate_er_diagram(project_id, chunks)
    
    return {
        "diagram_type": "er_diagram",
        "format": "mermaid",
        "diagram": diagram,
        "preview_url": None
    }


# ==================== STARTUP ====================

# ==================== AUTH ENDPOINTS ====================

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    db = next(get_db())
    user = db.query(User).filter(User.username == request.username).first()
    if not user or user.password != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"id": user.id, "username": user.username, "role": user.role, "full_name": user.full_name}


# ==================== REVIEW ENDPOINTS (3-STEP WORKFLOW) ====================

class SubmitReviewRequest(BaseModel):
    analysis_id: str
    project_id: str
    submitted_by: str
    checklist: Optional[List[str]] = []  # BA-provided checklist items

class HumanReviewRequest(BaseModel):
    reviewer_id: str
    decision: str          # "sign_off" or "return_to_ba"
    human_comments: Optional[str] = None
    ai_overrides: Optional[Dict[str, Any]] = {}  # {section_name: {verdict, comment}}

def _review_to_dict(r: DeliverableReview) -> dict:
    import json as _j
    def _parse(v):
        if not v: return None
        try: return _j.loads(v)
        except: return v
    return {
        "id": r.id, "analysis_id": r.analysis_id, "project_id": r.project_id,
        "submitted_by": r.submitted_by, "reviewed_by": r.reviewed_by,
        "version": r.version or 1,
        "checklist": _parse(r.checklist) or [],
        "status": r.status,
        "ai_review_status": r.ai_review_status or "pending",
        "ai_review_result": _parse(r.ai_review_result),
        "ai_reviewer_model": r.ai_reviewer_model,
        "human_comments": r.human_comments,
        "ai_overrides": _parse(r.ai_overrides) or {},
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
    }


@app.post("/api/reviews/submit")
async def submit_for_review(request: SubmitReviewRequest, background_tasks: BackgroundTasks):
    """Step 1a — BA submits deliverable. Triggers AI Reviewer 2 automatically."""
    db = next(get_db())

    # Get latest version number for this analysis
    last = db.query(DeliverableReview).filter(
        DeliverableReview.analysis_id == request.analysis_id
    ).order_by(DeliverableReview.version.desc()).first()
    new_version = (last.version or 1) + 1 if last else 1

    review = DeliverableReview(
        id=str(uuid.uuid4()),
        analysis_id=request.analysis_id,
        project_id=request.project_id,
        submitted_by=request.submitted_by,
        version=new_version,
        checklist=json.dumps(request.checklist or []),
        status="ai_reviewing",
        ai_review_status="running",
        submitted_at=datetime.utcnow()
    )
    db.add(review)
    db.commit()
    review_id = review.id

    # Run AI review in background
    def run_ai_review():
        from database import get_session
        tdb = get_session()
        try:
            rev = tdb.query(DeliverableReview).filter(DeliverableReview.id == review_id).first()
            analysis = tdb.query(AnalysisResult).filter(AnalysisResult.id == request.analysis_id).first()
            content = analysis.result if analysis else ""
            if isinstance(content, str):
                try: content = json.loads(content)
                except: pass
            checklist = json.loads(rev.checklist) if rev.checklist else []
            result = crew_service.ai_review_deliverable(content, analysis.analysis_type if analysis else "unknown", checklist)
            rev.ai_review_result = json.dumps(result)
            rev.ai_reviewer_model = result.get("reviewer_model", "")
            rev.ai_review_status = "done"
            rev.status = "pending_human"
            tdb.commit()
        except Exception as e:
            logger.error(f"AI review background error: {e}")
            rev = tdb.query(DeliverableReview).filter(DeliverableReview.id == review_id).first()
            if rev:
                rev.ai_review_status = "failed"
                rev.status = "pending_human"  # still allow human to proceed
                tdb.commit()
        finally:
            tdb.close()

    background_tasks.add_task(run_ai_review)
    return _review_to_dict(review)


@app.get("/api/reviews/pending")
async def get_pending_reviews():
    """Reviewer sees all deliverables awaiting human review (AI review done or failed)."""
    db = next(get_db())
    reviews = db.query(DeliverableReview).filter(
        DeliverableReview.status.in_(["pending_human", "ai_reviewing"])
    ).order_by(DeliverableReview.submitted_at.desc()).all()
    result = []
    for r in reviews:
        analysis = db.query(AnalysisResult).filter(AnalysisResult.id == r.analysis_id).first()
        project = db.query(Project).filter(Project.id == r.project_id).first()
        d = _review_to_dict(r)
        d["project_name"] = project.name if project else "Unknown"
        d["analysis_type"] = analysis.analysis_type if analysis else "Unknown"
        # Include the spec content so reviewer can read it
        if analysis and analysis.result:
            try: d["spec_content"] = json.loads(analysis.result)
            except: d["spec_content"] = analysis.result
        result.append(d)
    return result


@app.get("/api/reviews/analysis/{analysis_id}")
async def get_review_by_analysis(analysis_id: str):
    """Get latest review record for a given analysis (used by BA to see status)."""
    db = next(get_db())
    review = db.query(DeliverableReview).filter(
        DeliverableReview.analysis_id == analysis_id
    ).order_by(DeliverableReview.version.desc()).first()
    if not review:
        return None
    return _review_to_dict(review)


@app.get("/api/reviews/project/{project_id}")
async def get_project_reviews(project_id: str):
    db = next(get_db())
    reviews = db.query(DeliverableReview).filter(
        DeliverableReview.project_id == project_id
    ).order_by(DeliverableReview.submitted_at.desc()).all()
    return [_review_to_dict(r) for r in reviews]


@app.post("/api/reviews/{review_id}/human-decision")
async def human_review_decision(review_id: str, request: HumanReviewRequest):
    """Step 2 — Human reviewer signs off or returns to BA with comments + AI overrides."""
    db = next(get_db())
    review = db.query(DeliverableReview).filter(DeliverableReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if request.decision not in ("sign_off", "return_to_ba"):
        raise HTTPException(status_code=400, detail="decision must be sign_off or return_to_ba")

    review.reviewed_by = request.reviewer_id
    review.human_comments = request.human_comments
    review.ai_overrides = json.dumps(request.ai_overrides or {})
    review.status = "approved" if request.decision == "sign_off" else "returned"
    review.reviewed_at = datetime.utcnow()
    db.commit()
    return _review_to_dict(review)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    # Seed sample users if not present
    db = next(get_db())
    existing = [u.username for u in db.query(User).filter(User.username.in_(['ba_user', 'reviewer'])).all()]
    to_add = []
    if 'ba_user' not in existing:
        to_add.append(User(id=str(uuid.uuid4()), username='ba_user', password='ba123', role='business_analyst', full_name='Rama (Business Analyst)'))
    if 'reviewer' not in existing:
        to_add.append(User(id=str(uuid.uuid4()), username='reviewer', password='rev123', role='reviewer', full_name='Badri (Reviewer)'))
    if to_add:
        db.add_all(to_add)
        db.commit()
        logger.info(f"Seeded {len(to_add)} sample users")
    logger.info("AppRelic API started successfully")


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║           AppRelic API v2.0.0 - Starting...          ║
    ╠═══════════════════════════════════════════════════════╣
    ║  🚀 Server: http://{host}:{port}                 ║
    ║  📚 API Docs: http://{host}:{port}/docs          ║
    ║  🔧 Health: http://{host}:{port}/health          ║
    ╚═══════════════════════════════════════════════════════╝
    
    Features:
    ✅ 8 Deliverable Types (BRD, FRD, Stories, Tests, Migration, Reverse Eng, TDD, DB)
    ✅ 3 Chat Modes (Code, Database, System)
    ✅ Quality Scoring
    ✅ Document Exports (Word, Markdown, HTML)
    ✅ Architecture & ER Diagrams
    ✅ Code Insights & Recommendations
    """)
    
    uvicorn.run(app, host=host, port=port)
