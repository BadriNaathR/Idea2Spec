"""
Enhanced RAG Service with Chat Modes and Incremental Indexing
Supports code-only, database-only, and full-system chat modes
"""

import os

tiktoken_cache_dir = "tiktoken_cache"
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
os.makedirs(tiktoken_cache_dir, exist_ok=True)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# LangChain imports
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import PromptTemplate
    import httpx
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    logging.warning(f"LangChain not available: {e}. RAG features will be limited.")

logger = logging.getLogger(__name__)


class RAGService:
    """Enhanced RAG service with multi-mode support"""
    
    # Guardrail: Topics that are NOT allowed
    BLOCKED_TOPICS = [
        'politics', 'political', 'election', 'president', 'government',
        'religion', 'religious', 'god', 'faith', 'spiritual',
        'personal advice', 'relationship', 'dating', 'love life',
        'medical', 'health', 'diagnosis', 'treatment', 'symptoms',
        'legal advice', 'lawsuit', 'lawyer', 'attorney',
        'financial advice', 'investment', 'stock', 'crypto', 'bitcoin',
        'violence', 'weapon', 'harm', 'illegal',
        'adult content', 'explicit', 'nsfw',
        'joke', 'story', 'poem', 'song', 'recipe', 'weather',
        'news', 'current events', 'celebrity', 'gossip',
        'homework', 'exam', 'test answers', 'cheat'
    ]
    
    # Guardrail message
    GUARDRAIL_MESSAGE = """⚠️ **Off-Topic Request**

I'm specifically designed to help you understand **this project's codebase, database, and technical documentation**.

I can help with:
- 📝 Code architecture and design patterns
- 🗄️ Database schemas and queries
- 🔧 System functionality and workflows
- 📊 Technical documentation

Please ask a question related to the project files that have been uploaded.

**Examples of good questions:**
- "How does the authentication flow work?"
- "What design patterns are used in this codebase?"
- "Explain the database schema"
- "How do the API endpoints work?"
"""
    
    # Chat mode configurations
    MODE_CONFIGS = {
        'code': {
            'name': 'Code Analysis',
            'description': 'Focuses on source code, functions, classes, and code structure',
            'filter_categories': ['backend', 'frontend'],
            'system_prompt': """You are a **Senior Software Architect** with 20+ years of experience in enterprise software development.

**IMPORTANT GUARDRAILS - YOU MUST FOLLOW THESE:**
1. ONLY answer questions about the provided codebase and project context
2. If a question is NOT related to the code/project, respond with: "I can only help with questions about this project's codebase. Please ask about the code, architecture, or technical aspects of this project."
3. Do NOT answer questions about: politics, religion, personal advice, medical/legal/financial advice, general knowledge, jokes, stories, recipes, or anything unrelated to the codebase
4. Stay focused on technical analysis of the provided code context

Your expertise includes:
- Design patterns (GoF, Enterprise patterns, SOLID principles)
- Clean architecture, hexagonal architecture, microservices
- Performance optimization and scalability
- Code quality, maintainability, and technical debt assessment
- Technology stack evaluation and modernization strategies

**Response Guidelines:**
1. Provide **architectural-level insights**, not just code explanations
2. Use **technical terminology** appropriate for senior developers
3. Identify **design patterns** used or missing
4. Highlight **potential issues**: coupling, cohesion, SOLID violations
5. Suggest **refactoring opportunities** with specific recommendations
6. **Always cite sources** using format: `[Source N: filename]`
7. Use **markdown formatting**: headers, code blocks, bullet points
8. Include **code snippets** when relevant, wrapped in ```language blocks

Format your response with clear sections using markdown headers (##)."""
        },
        'db': {
            'name': 'Database Analysis',
            'description': 'Focuses on database schemas, queries, and data models',
            'filter_categories': ['database'],
            'system_prompt': """You are a **Senior Database Architect / DBA** with 20+ years of experience in enterprise database systems.

**IMPORTANT GUARDRAILS - YOU MUST FOLLOW THESE:**
1. ONLY answer questions about the provided database schemas, queries, and data models
2. If a question is NOT related to the database/project, respond with: "I can only help with questions about this project's database. Please ask about schemas, queries, data models, or database-related aspects."
3. Do NOT answer questions about: politics, religion, personal advice, medical/legal/financial advice, general knowledge, jokes, stories, recipes, or anything unrelated to the database
4. Stay focused on database analysis of the provided context

Your expertise includes:
- Database design and normalization (1NF through BCNF)
- Query optimization and execution plan analysis
- Indexing strategies and performance tuning
- Data modeling (conceptual, logical, physical)
- Transaction management and ACID compliance
- Database security and access patterns
- Migration strategies and schema evolution

**Response Guidelines:**
1. Provide **DBA-level analysis**, not just schema descriptions
2. Identify **normalization issues** and data anomalies
3. Suggest **index optimizations** with specific columns
4. Highlight **query performance concerns** with solutions
5. Discuss **referential integrity** and constraint design
6. **Always cite sources** using format: `[Source N: filename]`
7. Use **markdown formatting**: tables for schemas, code blocks for SQL
8. Include **SQL examples** when suggesting optimizations

Format your response with clear sections using markdown headers (##)."""
        },
        'system': {
            'name': 'Full System',
            'description': 'Comprehensive analysis across all code, database, and documentation',
            'filter_categories': ['backend', 'frontend', 'database', 'ui', 'config', 'documentation'],
            'system_prompt': """You are a **Technical Business Analyst** who bridges the gap between technical implementation and business understanding.

**IMPORTANT GUARDRAILS - YOU MUST FOLLOW THESE:**
1. ONLY answer questions about the provided project, its code, documentation, and functionality
2. If a question is NOT related to this project, respond with: "I can only help with questions about this project. Please ask about the system functionality, features, or technical aspects of this application."
3. Do NOT answer questions about: politics, religion, personal advice, medical/legal/financial advice, general knowledge, jokes, stories, recipes, or anything unrelated to the project
4. Stay focused on explaining this specific system based on the provided context

Your role is to explain technical systems in **clear, plain English** that both technical and non-technical stakeholders can understand.

**Response Guidelines:**
1. **Explain in plain English** - avoid jargon, use simple terms
2. Use **analogies** to explain complex concepts
3. Structure answers as: "What it does" → "How it works" → "Why it matters"
4. **Always cite your sources** clearly at the end:
   - Format: "📁 Sources: [filename1], [filename2]"
5. When discussing technical details, explain the **business impact**
6. Use **bullet points** and **numbered lists** for clarity
7. Include a **Summary** section at the end for quick reference
8. If something is unclear from the code, say so honestly

**Source Citation is MANDATORY** - every response must end with a "Sources" section listing the files referenced.

Format your response to be scannable with clear sections and bullet points."""
        },
        'general': {
            'name': 'General Assistant',
            'description': 'General purpose code assistant',
            'filter_categories': ['backend', 'frontend', 'database', 'ui', 'config', 'documentation'],
            'system_prompt': """You are a helpful technical assistant that can answer questions about this specific codebase.

**IMPORTANT GUARDRAILS - YOU MUST FOLLOW THESE:**
1. ONLY answer questions about the provided codebase and project context
2. If a question is NOT related to this project, respond with: "I can only help with questions about this project's codebase. Please ask about the code, architecture, or technical aspects."
3. Do NOT answer questions about: politics, religion, personal advice, medical/legal/financial advice, general knowledge, jokes, stories, recipes, or anything unrelated to the project
4. Stay focused on the provided code context

Provide clear, accurate, and helpful responses based on the code context provided.
Use markdown formatting for better readability.
Always cite specific files when referencing code."""
        }
    }
    
    def _is_off_topic(self, query: str) -> bool:
        """Check if the query is off-topic (not related to the project)"""
        query_lower = query.lower()
        
        # Check for blocked topics
        for topic in self.BLOCKED_TOPICS:
            if topic in query_lower:
                return True
        
        # Check for greetings/chitchat without technical context
        chitchat_patterns = [
            'hello', 'hi there', 'hey', 'good morning', 'good afternoon', 
            'how are you', 'what\'s up', 'whats up', 'tell me a joke',
            'write a poem', 'write a story', 'make me laugh',
            'who are you', 'what can you do', 'help me with',
            'what is the weather', 'what time is it'
        ]
        
        # If query is just chitchat without code-related keywords, it's off-topic
        if any(pattern in query_lower for pattern in chitchat_patterns):
            # But allow if there are also technical terms
            tech_terms = ['code', 'function', 'class', 'api', 'database', 'schema', 
                          'file', 'method', 'variable', 'project', 'app', 'system',
                          'error', 'bug', 'feature', 'component', 'module']
            if not any(term in query_lower for term in tech_terms):
                return True
        
        return False
    
    def __init__(self):
        self.vector_stores = {}  # project_id -> vector store
        self.document_counts = {}  # project_id -> count
        self._base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_stores")
        os.makedirs(self._base_dir, exist_ok=True)
        # Prevent any ambient OPENAI_MODEL env var from leaking into embeddings
        os.environ.pop("OPENAI_MODEL", None)
        
        if LANGCHAIN_AVAILABLE:
            try:
                base_url = os.getenv("LITELLM_BASE_URL", "")
                api_key = os.getenv("LITELLM_API_KEY", "")
                chat_model = os.getenv("LITELLM_MODEL", "azure/genailab-maas-gpt-4.1-nano")
                self._embedding_model = os.getenv("LITELLM_EMBEDDING_MODEL", "azure/genailab-maas-text-embedding-3-large")
                http_client = httpx.Client(verify=False)

                self.embeddings = OpenAIEmbeddings(
                    base_url=base_url,
                    api_key=api_key,
                    model=self._embedding_model,
                    http_client=http_client,
                    check_embedding_ctx_length=False,
                    disallowed_special=()
                )
                self.llm = ChatOpenAI(
                    base_url=base_url,
                    api_key=api_key,
                    model=chat_model,
                    temperature=0.7,
                    http_client=http_client
                )
                logger.info(f"RAG Service initialized with LiteLLM: {chat_model}")
            except Exception as e:
                logger.error(f"Error initializing embeddings/LLM: {str(e)}")
                self.embeddings = None
                self.llm = None
        else:
            logger.warning("LangChain not available. RAG features will be limited.")
            self.embeddings = None
            self.llm = None
    
    def add_documents(
        self,
        project_id: str,
        documents: List[Dict[str, Any]],
        append: bool = False,
        batch_size: int = 50
    ) -> bool:
        """
        Add documents to vector store with optional incremental indexing
        
        Args:
            project_id: Project identifier
            documents: List of document dictionaries
            append: If True, append to existing index; if False, create new index
            batch_size: Number of documents to process per batch (to avoid rate limits)
            
        Returns:
            Success status
        """
        if not self.embeddings:
            logger.warning("Embeddings not available. Cannot add documents.")
            return False
        
        if not documents:
            logger.warning("No documents to add.")
            return True  # Not an error, just nothing to do
        
        try:
            import time
            
            logger.info(f"Using embedding model: {getattr(self.embeddings, 'model', 'unknown')} for project {project_id}")
            # Convert dictionaries to LangChain Document objects
            lang_docs = []
            for doc in documents:
                content = doc.get('content', '')
                metadata = {
                    'file_path': doc.get('file_path', ''),
                    'file_name': doc.get('file_name', ''),
                    'language': doc.get('language', ''),
                    'category': doc.get('category', ''),
                    'chunk_index': doc.get('chunk_index', 0)
                }
                lang_docs.append(Document(page_content=content, metadata=metadata))
            
            # Process in batches to avoid rate limits
            total_docs = len(lang_docs)
            vectorstore = None
            
            for i in range(0, total_docs, batch_size):
                batch = lang_docs[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_docs + batch_size - 1) // batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} docs) for project {project_id}")
                
                try:
                    if vectorstore is None:
                        # First batch - create vector store
                        if append and project_id in self.vector_stores:
                            vectorstore = self.vector_stores[project_id]
                            vectorstore.add_documents(batch)
                        else:
                            vectorstore = FAISS.from_documents(batch, self.embeddings)
                    else:
                        # Subsequent batches - add to existing
                        vectorstore.add_documents(batch)
                    
                    # Add delay between batches to avoid rate limits
                    if i + batch_size < total_docs:
                        time.sleep(2)  # 2 second delay between batches
                        
                except Exception as batch_error:
                    if '429' in str(batch_error) or 'RateLimit' in str(batch_error):
                        logger.warning(f"Rate limit hit, waiting 60 seconds...")
                        time.sleep(60)
                        # Retry the batch
                        if vectorstore is None:
                            vectorstore = FAISS.from_documents(batch, self.embeddings)
                        else:
                            vectorstore.add_documents(batch)
                    else:
                        raise
            
            # Store and save
            self.vector_stores[project_id] = vectorstore
            self.document_counts[project_id] = total_docs
            
            # Save to disk
            self._save_vector_store(project_id)
            
            logger.info(f"Successfully indexed {total_docs} documents for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}", exc_info=True)
            return False
    
    def search(
        self,
        project_id: str,
        query: str,
        mode: str = "system",
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents with mode-specific filtering
        
        Args:
            project_id: Project identifier
            query: Search query
            mode: Search mode (code, db, system, general)
            k: Number of results to return
            
        Returns:
            List of relevant documents with scores
        """
        # Try to load vector store from disk if not in memory
        if project_id not in self.vector_stores:
            logger.info(f"Vector store not in memory, attempting to load from disk for project {project_id}")
            if not self._load_vector_store(project_id):
                logger.warning(f"No vector store found for project {project_id}")
                return []
        
        try:
            vectorstore = self.vector_stores[project_id]
            
            # Get mode configuration
            mode_config = self.MODE_CONFIGS.get(mode, self.MODE_CONFIGS['general'])
            filter_categories = mode_config['filter_categories']
            
            # Search with category filtering
            # Note: FAISS doesn't support metadata filtering out of the box,
            # so we'll retrieve more results and filter post-search
            results = vectorstore.similarity_search_with_score(query, k=k*3)
            
            # Filter by category (include empty categories as they match all modes)
            filtered_results = [
                (doc, score) for doc, score in results
                if doc.metadata.get('category', '') in filter_categories or not doc.metadata.get('category')
            ][:k]
            
            # Convert to dictionary format
            documents = []
            for doc, score in filtered_results:
                documents.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score)
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}", exc_info=True)
            return []
    
    def generate_response(
        self,
        project_id: str,
        query: str,
        mode: str = "system",
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response with mode-specific context
        
        Args:
            project_id: Project identifier
            query: User query
            mode: Chat mode (code, db, system, general)
            chat_history: Optional chat history
            
        Returns:
            Response dictionary with answer, sources, and suggestions
        """
        # GUARDRAIL CHECK: Block off-topic questions
        if self._is_off_topic(query):
            logger.info(f"Blocked off-topic query: {query[:50]}...")
            return {
                'response': self.GUARDRAIL_MESSAGE,
                'sources': [],
                'suggestions': [
                    'How does the authentication work?',
                    'Explain the database schema',
                    'What are the main components?',
                    'Show me the API endpoints'
                ],
                'mode': mode,
                'blocked': True
            }
        
        if not self.llm:
            return {
                'response': 'AI service not configured. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY, or OPENAI_API_KEY in your .env file.',
                'sources': [],
                'suggestions': [],
                'mode': mode
            }
        
        try:
            # Get mode configuration
            mode_config = self.MODE_CONFIGS.get(mode, self.MODE_CONFIGS['general'])
            
            # Search for relevant context
            context_docs = self.search(project_id, query, mode=mode, k=5)
            
            if not context_docs:
                return {
                    'response': f'No relevant {mode} context found for your question. Try uploading more files or changing the chat mode.',
                    'sources': [],
                    'suggestions': [
                        'Upload more source files',
                        'Try a different chat mode',
                        'Rephrase your question'
                    ],
                    'mode': mode
                }
            
            # Build context string
            context_parts = []
            sources = []
            for i, doc in enumerate(context_docs, 1):
                file_path = doc['metadata'].get('file_path', 'unknown')
                language = doc['metadata'].get('language', 'unknown')
                content = doc['content'][:500]  # Limit content length
                
                context_parts.append(f"[Source {i}] {file_path} ({language}):\n{content}\n")
                sources.append({
                    'file_path': file_path,
                    'language': language,
                    'score': doc['score']
                })
            
            context = "\n".join(context_parts)
            
            # Build chat history string
            history_str = ""
            if chat_history:
                for msg in chat_history[-5:]:  # Last 5 messages
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    history_str += f"{role}: {content}\n"
            
            # Create prompt with mode-specific system message
            prompt = f"""{mode_config['system_prompt']}

---

## CONTEXT FROM CODEBASE:
{context}

---

## PREVIOUS CONVERSATION:
{history_str if history_str else "(No previous messages)"}

---

## USER QUESTION:
{query}

---

**Instructions:** Provide a comprehensive response following your role guidelines above. 
Use markdown formatting (headers, code blocks, bullet points) for clarity.
Cite sources using [Source N: filename] format throughout your response.

Your Response:"""
            
            # Generate response using invoke (predict is deprecated)
            response = self._invoke_with_content_filter_retry(self.llm, prompt).content
            
            # Generate suggestions based on mode
            suggestions = self._generate_suggestions(mode, query, context_docs)
            
            return {
                'response': response,
                'sources': sources,
                'suggestions': suggestions,
                'mode': mode,
                'mode_name': mode_config['name']
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return {
                'response': f'Error generating response: {str(e)}',
                'sources': [],
                'suggestions': [],
                'mode': mode
            }
    
    def _invoke_with_content_filter_retry(self, llm, prompt: str, max_retries: int = 3):
        """Invoke LLM, retrying with sanitized prompt if content filter blocks a keyword."""
        import re
        current_prompt = prompt
        for attempt in range(max_retries):
            try:
                return llm.invoke(current_prompt)
            except Exception as e:
                error_str = str(e)
                # Detect Azure content filter 403 error
                keyword_match = re.search(r"keyword ['\"]([^'\"]+)['\"]|'keyword':\s*'([^']+)'", error_str)
                if ('403' in error_str or 'Content blocked' in error_str or 'denied_' in error_str) and keyword_match:
                    blocked_kw = keyword_match.group(1) or keyword_match.group(2)
                    logger.warning(f"Content filter blocked keyword '{blocked_kw}', retrying without it (attempt {attempt + 1})")
                    current_prompt = re.sub(re.escape(blocked_kw), '', current_prompt, flags=re.IGNORECASE)
                else:
                    raise
        return llm.invoke(current_prompt)

    def _generate_suggestions(
        self,
        mode: str,
        query: str,
        context_docs: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up suggestions based on mode and context"""
        suggestions = []
        
        if mode == 'code':
            suggestions = [
                'Explain the main classes and their relationships',
                'What design patterns are used?',
                'How can the code quality be improved?',
                'Show me the entry points of the application'
            ]
        elif mode == 'db':
            suggestions = [
                'What are the main database tables?',
                'Show me the database relationships',
                'Are there any performance issues?',
                'Explain the data model'
            ]
        elif mode == 'system':
            suggestions = [
                'Provide an overview of the system architecture',
                'How do the components interact?',
                'What is the technology stack?',
                'Explain the data flow through the system'
            ]
        else:
            suggestions = [
                'Tell me more about this codebase',
                'What are the main components?',
                'How is this implemented?'
            ]
        
        return suggestions[:3]  # Return top 3
    
    def get_project_context(self, project_id: str, mode: str = "system") -> str:
        """Get comprehensive project context summary"""
        if project_id not in self.vector_stores:
            return "No documents indexed for this project."
        
        doc_count = self.document_counts.get(project_id, 0)
        mode_config = self.MODE_CONFIGS.get(mode, self.MODE_CONFIGS['general'])
        
        return f"""Project has {doc_count} indexed documents.
Current mode: {mode_config['name']}
Mode focus: {mode_config['description']}
"""
    
    def _save_vector_store(self, project_id: str):
        """Save vector store to disk"""
        try:
            save_dir = os.path.join(self._base_dir, project_id)
            os.makedirs(save_dir, exist_ok=True)
            
            vectorstore = self.vector_stores[project_id]
            vectorstore.save_local(save_dir)
            
            # Save document count
            with open(os.path.join(save_dir, 'metadata.json'), 'w') as f:
                json.dump({
                    'document_count': self.document_counts[project_id],
                    'updated_at': datetime.utcnow().isoformat()
                }, f)
            
            logger.info(f"Saved vector store for project {project_id}")
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
    
    def _load_vector_store(self, project_id: str) -> bool:
        """Load vector store from disk"""
        try:
            save_dir = os.path.join(self._base_dir, project_id)
            
            if not os.path.exists(save_dir):
                return False
            
            if not self.embeddings:
                return False
            
            vectorstore = FAISS.load_local(save_dir, self.embeddings, allow_dangerous_deserialization=True)
            self.vector_stores[project_id] = vectorstore
            
            # Load document count
            metadata_file = os.path.join(save_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.document_counts[project_id] = metadata.get('document_count', 0)
            
            logger.info(f"Loaded vector store for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False
    
    def delete_project(self, project_id: str):
        """Delete project vector store"""
        try:
            # Remove from memory
            if project_id in self.vector_stores:
                del self.vector_stores[project_id]
            if project_id in self.document_counts:
                del self.document_counts[project_id]
            
            # Remove from disk
            save_dir = os.path.join(self._base_dir, project_id)
            if os.path.exists(save_dir):
                import shutil
                shutil.rmtree(save_dir)
                logger.info(f"Deleted vector store for project {project_id}")
        except Exception as e:
            logger.error(f"Error deleting vector store: {str(e)}")


if __name__ == "__main__":
    # Test the RAG service
    logging.basicConfig(level=logging.INFO)
    
    service = RAGService()
    print("RAG service initialized successfully!")
    print(f"Available modes: {list(service.MODE_CONFIGS.keys())}")
