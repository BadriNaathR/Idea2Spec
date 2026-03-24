"""
Enhanced Code Analyzer with GitHub Integration
Supports 20+ programming languages with detailed metadata extraction
"""

import os
import re
import zipfile
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class GitHubIntegration:
    """Handle GitHub repository cloning and access"""
    
    @staticmethod
    def is_git_available() -> bool:
        """Check if git is installed"""
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def clone_repository(
        repo_url: str,
        branch: str = "main",
        access_token: Optional[str] = None,
        target_dir: Optional[str] = None
    ) -> str:
        """
        Clone a GitHub repository
        
        Args:
            repo_url: Repository URL
            branch: Branch name (default: main)
            access_token: Optional access token for private repos
            target_dir: Optional target directory
            
        Returns:
            Path to cloned repository
        """
        if not GitHubIntegration.is_git_available():
            raise RuntimeError("Git is not installed. Please install git to use GitHub integration.")
        
        # Create temporary directory if not provided
        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix="apprelic_repo_")
        
        # Add access token to URL if provided
        if access_token and "github.com" in repo_url:
            # Convert https://github.com/user/repo to https://token@github.com/user/repo
            repo_url = repo_url.replace("https://", f"https://{access_token}@")
        
        try:
            # Clone repository
            logger.info(f"Cloning repository: {repo_url} (branch: {branch})")
            subprocess.run(
                ["git", "clone", "-b", branch, "--depth", "1", repo_url, target_dir],
                capture_output=True,
                check=True,
                text=True
            )
            logger.info(f"Repository cloned successfully to: {target_dir}")
            return target_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")


class CodeAnalyzer:
    """Analyze code files and extract metadata"""
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        # Backend
        '.py': 'python',
        '.cs': 'csharp',
        '.java': 'java',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.rs': 'rust',
        
        # Frontend
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.vue': 'vue',
        
        # Web
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        
        # Database
        '.sql': 'sql',
        
        # Config
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.conf': 'config',
        
        # Documentation
        '.md': 'markdown',
        '.txt': 'text',
        '.rst': 'restructuredtext',
    }
    
    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', 'venv', 'env', '.git', '.svn', '__pycache__',
        'dist', 'build', 'target', 'bin', 'obj', '.next', '.nuxt',
        'coverage', '.pytest_cache', '.mypy_cache', '.tox',
        'vendor', 'packages', '.idea', '.vscode'
    }
    
    # Max file size (2MB)
    MAX_FILE_SIZE = 2 * 1024 * 1024
    
    def __init__(self):
        self.file_count = 0
        self.total_lines = 0
        self.total_size = 0
        self.language_stats = {}
    
    def analyze_directory(self, directory: str) -> List[Dict[str, Any]]:
        """
        Analyze all code files in a directory
        
        Args:
            directory: Path to directory
            
        Returns:
            List of document metadata dictionaries
        """
        documents = []
        
        for root, dirs, files in os.walk(directory):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Check if supported extension
                if ext in self.SUPPORTED_EXTENSIONS:
                    try:
                        file_size = os.path.getsize(file_path)
                        
                        # Skip files that are too large
                        if file_size > self.MAX_FILE_SIZE:
                            logger.warning(f"Skipping large file: {file_path} ({file_size} bytes)")
                            continue
                        
                        # Read and analyze file
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Extract metadata
                        metadata = self._extract_metadata(content, file_path, ext)
                        
                        # Chunk content
                        chunks = self._chunk_content(content, file_path, metadata)
                        documents.extend(chunks)
                        
                        # Update statistics
                        self.file_count += 1
                        self.total_lines += metadata['lines_of_code']
                        self.total_size += file_size
                        
                        language = self.SUPPORTED_EXTENSIONS[ext]
                        self.language_stats[language] = self.language_stats.get(language, 0) + 1
                        
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {str(e)}")
        
        logger.info(f"Analyzed {self.file_count} files, {self.total_lines} lines of code")
        return documents
    
    def analyze_github_repo(
        self,
        repo_url: str,
        branch: str = "main",
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Clone and analyze a GitHub repository
        
        Args:
            repo_url: Repository URL
            branch: Branch name
            access_token: Optional access token
            
        Returns:
            List of document metadata dictionaries
        """
        temp_dir = None
        try:
            # Clone repository
            temp_dir = GitHubIntegration.clone_repository(repo_url, branch, access_token)
            
            # Analyze cloned repository
            documents = self.analyze_directory(temp_dir)
            
            return documents
            
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
    
    def analyze_zip_file(self, zip_path: str) -> List[Dict[str, Any]]:
        """
        Extract and analyze a ZIP file
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            List of document metadata dictionaries
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="apprelic_zip_")
            
            # Extract ZIP
            logger.info(f"Extracting ZIP file: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Analyze extracted files
            documents = self.analyze_directory(temp_dir)
            
            return documents
            
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
    
    def _extract_metadata(self, content: str, file_path: str, extension: str) -> Dict[str, Any]:
        """
        Extract metadata from code content
        
        Args:
            content: File content
            file_path: Path to file
            extension: File extension
            
        Returns:
            Metadata dictionary
        """
        language = self.SUPPORTED_EXTENSIONS.get(extension, 'unknown')
        
        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'extension': extension,
            'language': language,
            'lines_of_code': len(content.splitlines()),
            'size_bytes': len(content.encode('utf-8')),
            'category': self._categorize_file(file_path, language),
        }
        
        # Language-specific metadata extraction
        if language in ['python', 'javascript', 'typescript', 'java', 'csharp', 'go']:
            metadata.update(self._extract_code_elements(content, language))
        
        return metadata
    
    def _extract_code_elements(self, content: str, language: str) -> Dict[str, Any]:
        """Extract code elements like classes, functions, imports"""
        elements = {
            'classes': [],
            'functions': [],
            'imports': [],
            'comments': 0
        }
        
        # Python
        if language == 'python':
            elements['classes'] = re.findall(r'class\s+(\w+)', content)
            elements['functions'] = re.findall(r'def\s+(\w+)', content)
            elements['imports'] = re.findall(r'(?:from|import)\s+([\w\.]+)', content)
            elements['comments'] = len(re.findall(r'#.*$', content, re.MULTILINE))
        
        # JavaScript/TypeScript
        elif language in ['javascript', 'typescript']:
            elements['classes'] = re.findall(r'class\s+(\w+)', content)
            elements['functions'] = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*[=\(]', content)
            elements['imports'] = re.findall(r'import.*?from\s+[\'"]([^\'"]+)', content)
            elements['comments'] = len(re.findall(r'//.*$|/\*.*?\*/', content, re.MULTILINE | re.DOTALL))
        
        # Java
        elif language == 'java':
            elements['classes'] = re.findall(r'(?:class|interface)\s+(\w+)', content)
            elements['functions'] = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', content)
            elements['imports'] = re.findall(r'import\s+([\w\.]+)', content)
            elements['comments'] = len(re.findall(r'//.*$|/\*.*?\*/', content, re.MULTILINE | re.DOTALL))
        
        # C#
        elif language == 'csharp':
            elements['classes'] = re.findall(r'(?:class|interface|struct)\s+(\w+)', content)
            elements['functions'] = re.findall(r'(?:public|private|protected|internal)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', content)
            elements['imports'] = re.findall(r'using\s+([\w\.]+)', content)
            elements['comments'] = len(re.findall(r'//.*$|/\*.*?\*/', content, re.MULTILINE | re.DOTALL))
        
        # Go
        elif language == 'go':
            elements['functions'] = re.findall(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)', content)
            elements['imports'] = re.findall(r'import\s+(?:"([^"]+)"|`([^`]+)`)', content)
            elements['comments'] = len(re.findall(r'//.*$|/\*.*?\*/', content, re.MULTILINE | re.DOTALL))
        
        return elements
    
    def _categorize_file(self, file_path: str, language: str) -> str:
        """Categorize file based on path and language"""
        file_path_lower = file_path.lower()
        
        # Backend
        if language in ['python', 'java', 'csharp', 'go', 'ruby', 'php', 'kotlin', 'swift', 'rust']:
            return 'backend'
        
        # Frontend
        if language in ['javascript', 'typescript', 'vue'] or any(x in file_path_lower for x in ['components', 'pages', 'views']):
            return 'frontend'
        
        # UI/Styles
        if language in ['html', 'css', 'scss', 'sass', 'less']:
            return 'ui'
        
        # Database
        if language == 'sql' or 'migration' in file_path_lower or 'schema' in file_path_lower:
            return 'database'
        
        # Config
        if language in ['json', 'yaml', 'xml', 'toml', 'ini', 'config']:
            return 'config'
        
        # Documentation
        if language in ['markdown', 'text', 'restructuredtext']:
            return 'documentation'
        
        return 'other'
    
    def _chunk_content(
        self,
        content: str,
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Split content into overlapping chunks
        
        Args:
            content: File content
            file_path: Path to file
            metadata: File metadata
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Split content into chunks
        for i in range(0, len(content), chunk_size - overlap):
            chunk_content = content[i:i + chunk_size]
            
            # Skip very small chunks at the end
            if len(chunk_content) < 100:
                continue
            
            chunk = {
                'content': chunk_content,
                'file_path': file_path,
                'file_name': metadata['file_name'],
                'language': metadata['language'],
                'category': metadata['category'],
                'chunk_index': len(chunks),
                'metadata': metadata
            }
            
            chunks.append(chunk)
        
        # Return chunks, or if content was too small, return at least one chunk
        if chunks:
            return chunks
        else:
            return [{
                'content': content,
                'file_path': file_path,
                'file_name': metadata.get('file_name', file_path),
                'language': metadata.get('language', 'unknown'),
                'category': metadata.get('category', 'other'),
                'chunk_index': 0,
                'metadata': metadata
            }]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        return {
            'file_count': self.file_count,
            'total_lines': self.total_lines,
            'total_size_bytes': self.total_size,
            'language_stats': self.language_stats
        }


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    
    analyzer = CodeAnalyzer()
    
    # Test directory analysis
    # documents = analyzer.analyze_directory("./test_code")
    
    # Test GitHub analysis
    # documents = analyzer.analyze_github_repo("https://github.com/user/repo")
    
    print("Code analyzer initialized successfully!")
