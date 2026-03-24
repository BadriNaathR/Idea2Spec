"""
Insights Service - Code Analysis and Recommendations
Provides code hotspots, DB optimization, and modernization recommendations
"""

from typing import List, Dict, Any
import logging
import re
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class InsightsService:
    """Service for generating project insights and recommendations"""
    
    def __init__(self):
        pass
    
    def analyze_project(
        self,
        project_id: str,
        chunks: List[Any]
    ) -> Dict[str, Any]:
        """
        Analyze project and generate insights
        
        Args:
            project_id: Project ID
            chunks: Document chunks from codebase
            
        Returns:
            Dictionary with insights
        """
        try:
            # Analyze code complexity
            code_hotspots = self.analyze_code_complexity(chunks)
            
            # Analyze database
            db_optimizations = self.analyze_database_optimization(chunks)
            
            # Generate modernization recommendations
            modernization = self.recommend_modernization(chunks)
            
            # Analyze tech stack
            tech_stack = self.analyze_tech_stack(chunks)
            
            return {
                'code_hotspots': code_hotspots,
                'db_optimizations': db_optimizations,
                'modernization_recommendations': modernization,
                'tech_stack': tech_stack
            }
            
        except Exception as e:
            logger.error(f"Error analyzing project: {str(e)}")
            return self._get_default_insights()
    
    # ==================== CODE COMPLEXITY ANALYSIS ====================
    
    def analyze_code_complexity(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """
        Identify code hotspots based on complexity
        
        Returns list of hotspots with:
        - name: Module/file name
        - complexity: Estimated complexity score (0-100)
        - files: Number of files
        - lines: Lines of code
        - issues: List of potential issues
        """
        hotspots = []
        
        # Group by module/directory
        modules = defaultdict(lambda: {'files': set(), 'lines': 0, 'content': []})
        
        for chunk in chunks:
            file_path = getattr(chunk, 'file_path', '')
            content = getattr(chunk, 'content', '')
            language = getattr(chunk, 'language', '')
            
            # Extract module name from path
            if '/' in file_path:
                module = file_path.split('/')[0]
            else:
                module = 'Root'
            
            modules[module]['files'].add(file_path)
            modules[module]['lines'] += len(content.split('\n'))
            modules[module]['content'].append(content)
        
        # Analyze each module
        for module_name, module_data in modules.items():
            complexity_score = self._calculate_complexity_score(module_data)
            issues = self._identify_code_issues(module_data)
            
            hotspots.append({
                'name': module_name,
                'complexity': complexity_score,
                'files': len(module_data['files']),
                'lines': module_data['lines'],
                'issues': issues
            })
        
        # Sort by complexity (highest first)
        hotspots.sort(key=lambda x: x['complexity'], reverse=True)
        
        return hotspots[:10]  # Top 10 hotspots
    
    def _calculate_complexity_score(self, module_data: Dict[str, Any]) -> int:
        """Calculate complexity score for a module (0-100)"""
        score = 0
        full_content = '\n'.join(module_data['content'])
        
        # Factor 1: Lines of code (normalized)
        lines = module_data['lines']
        if lines > 5000:
            score += 30
        elif lines > 2000:
            score += 20
        elif lines > 1000:
            score += 10
        
        # Factor 2: Cyclomatic complexity indicators
        # Count conditionals
        conditionals = len(re.findall(r'\b(if|else|switch|case|while|for)\b', full_content))
        if conditionals > 100:
            score += 25
        elif conditionals > 50:
            score += 15
        elif conditionals > 20:
            score += 8
        
        # Factor 3: Nested levels (approximate)
        max_indent = 0
        for line in full_content.split('\n'):
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        
        if max_indent > 32:  # Very deep nesting
            score += 20
        elif max_indent > 16:
            score += 10
        
        # Factor 4: Number of functions/methods
        functions = len(re.findall(r'\bfunction\b|\bdef\b|\bpublic\s+\w+\s+\w+\(', full_content))
        if functions > 50:
            score += 15
        elif functions > 25:
            score += 8
        
        # Factor 5: File count
        if len(module_data['files']) > 20:
            score += 10
        elif len(module_data['files']) > 10:
            score += 5
        
        return min(score, 100)
    
    def _identify_code_issues(self, module_data: Dict[str, Any]) -> List[str]:
        """Identify potential code issues"""
        issues = []
        full_content = '\n'.join(module_data['content'])
        
        # Check for common issues
        if 'TODO' in full_content or 'FIXME' in full_content:
            issues.append("Contains TODO/FIXME comments")
        
        if len(re.findall(r'\btry\b', full_content)) < 2 and module_data['lines'] > 500:
            issues.append("Limited error handling")
        
        if 'console.log' in full_content or 'print(' in full_content:
            issues.append("Contains debug statements")
        
        # Check for long methods
        method_blocks = re.findall(r'(function|def|public\s+\w+)\s+\w+[^{]*{[^}]{500,}', full_content, re.DOTALL)
        if len(method_blocks) > 5:
            issues.append("Contains long methods (>500 chars)")
        
        # Check for code duplication indicators
        lines = full_content.split('\n')
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(lines) > 100 and len(unique_lines) / len(lines) < 0.7:
            issues.append("Potential code duplication")
        
        return issues[:5]  # Limit to 5 issues
    
    # ==================== DATABASE OPTIMIZATION ====================
    
    def analyze_database_optimization(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """
        Analyze database for optimization opportunities
        
        Returns list of suggestions with:
        - type: warning, info, success
        - title: Issue title
        - impact: Description of impact
        - recommendation: What to do
        """
        suggestions = []
        
        # Filter for database-related chunks
        db_chunks = [
            chunk for chunk in chunks
            if getattr(chunk, 'language', '') in ['sql', 'plsql', 'tsql'] or
            'database' in getattr(chunk, 'file_path', '').lower()
        ]
        
        if not db_chunks:
            return [{
                'type': 'info',
                'title': 'No database files detected',
                'impact': 'Unable to analyze database optimization',
                'recommendation': 'Add SQL schema files for analysis'
            }]
        
        # Analyze SQL code
        all_sql = '\n'.join([getattr(chunk, 'content', '') for chunk in db_chunks])
        
        # Check 1: Missing indexes
        table_scans = re.findall(r'FROM\s+(\w+)', all_sql, re.IGNORECASE)
        where_clauses = re.findall(r'WHERE\s+(\w+)', all_sql, re.IGNORECASE)
        
        if table_scans and where_clauses:
            # Find frequently queried tables
            table_counts = Counter(table_scans)
            where_counts = Counter(where_clauses)
            
            for table, count in table_counts.most_common(3):
                if count > 5:  # Frequently queried
                    suggestions.append({
                        'type': 'warning',
                        'title': f'Consider adding index on {table}',
                        'impact': f'Table queried {count} times - may benefit from indexing',
                        'recommendation': f'CREATE INDEX idx_{table}_common ON {table}(column_name)'
                    })
        
        # Check 2: Large table detection
        create_table_matches = re.findall(
            r'CREATE\s+TABLE\s+(\w+)',
            all_sql,
            re.IGNORECASE
        )
        
        if len(create_table_matches) > 10:
            suggestions.append({
                'type': 'info',
                'title': 'Large number of tables detected',
                'impact': f'{len(create_table_matches)} tables - consider data partitioning',
                'recommendation': 'Review table sizes and implement partitioning for large tables'
            })
        
        # Check 3: Normalization
        # Look for repeated column patterns
        column_pattern = re.findall(r'(\w+)\s+(VARCHAR|INT|DATE|DECIMAL)', all_sql, re.IGNORECASE)
        column_names = [col[0] for col in column_pattern]
        duplicate_columns = [col for col, count in Counter(column_names).items() if count > 5]
        
        if duplicate_columns:
            suggestions.append({
                'type': 'info',
                'title': 'Potential normalization opportunities',
                'impact': f'Columns like {", ".join(duplicate_columns[:3])} appear in multiple tables',
                'recommendation': 'Review schema normalization to reduce redundancy'
            })
        
        # Check 4: No foreign keys detected
        fk_count = len(re.findall(r'FOREIGN\s+KEY', all_sql, re.IGNORECASE))
        table_count = len(create_table_matches)
        
        if table_count > 5 and fk_count < 3:
            suggestions.append({
                'type': 'warning',
                'title': 'Limited foreign key constraints',
                'impact': 'Missing foreign keys can lead to data integrity issues',
                'recommendation': 'Add foreign key constraints to enforce referential integrity'
            })
        else:
            suggestions.append({
                'type': 'success',
                'title': 'Good use of foreign key constraints',
                'impact': 'Foreign keys help maintain data integrity',
                'recommendation': 'Continue enforcing referential integrity'
            })
        
        # Check 5: Query optimization
        select_star = len(re.findall(r'SELECT\s+\*', all_sql, re.IGNORECASE))
        if select_star > 5:
            suggestions.append({
                'type': 'warning',
                'title': 'Avoid SELECT * queries',
                'impact': f'{select_star} SELECT * queries found - impacts performance',
                'recommendation': 'Specify only required columns in SELECT statements'
            })
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    # ==================== MODERNIZATION RECOMMENDATIONS ====================
    
    def recommend_modernization(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """
        Generate modernization recommendations
        
        Returns list of recommendations with:
        - title: Recommendation title
        - description: Description
        - services: List of candidate microservices
        - tech_stack: Recommended technologies
        - priority: High, Medium, Low
        - effort: Estimated effort (weeks)
        """
        recommendations = []
        
        # Analyze current architecture
        tech_analysis = self.analyze_tech_stack(chunks)
        languages = tech_analysis.get('languages', [])
        frameworks = tech_analysis.get('frameworks', [])
        
        # Recommendation 1: Microservices if monolithic
        file_count = len(chunks)
        if file_count > 100:
            # Identify potential microservices
            services = self._identify_microservice_candidates(chunks)
            
            recommendations.append({
                'title': 'Microservices Architecture on Azure Kubernetes Service',
                'description': f'Application has {file_count} files - good candidate for decomposition',
                'services': services,
                'tech_stack': [
                    'Azure Kubernetes Service (AKS)',
                    'Azure Service Bus',
                    'Azure API Management',
                    'Azure Container Registry'
                ],
                'priority': 'High',
                'effort': 12,
                'benefits': [
                    'Independent scaling',
                    'Faster deployment cycles',
                    'Technology flexibility',
                    'Improved fault isolation'
                ]
            })
        
        # Recommendation 2: Cloud migration
        has_legacy_tech = any(
            lang in str(languages).lower() 
            for lang in ['vb', 'cobol', 'fortran', 'asp']
        )
        
        if has_legacy_tech or 'sql server' in str(frameworks).lower():
            recommendations.append({
                'title': 'Cloud-Native Migration to Azure',
                'description': 'Modernize legacy technology stack with Azure cloud services',
                'services': [],
                'tech_stack': [
                    'Azure App Service',
                    'Azure SQL Database',
                    'Azure Functions (serverless)',
                    'Azure DevOps',
                    'Azure Monitor'
                ],
                'priority': 'High',
                'effort': 16,
                'benefits': [
                    'Reduced infrastructure costs',
                    'Auto-scaling capabilities',
                    'High availability (99.95% SLA)',
                    'Built-in security'
                ]
            })
        
        # Recommendation 3: API-first architecture
        api_count = sum(1 for chunk in chunks if 'controller' in getattr(chunk, 'file_path', '').lower())
        
        if api_count > 0:
            recommendations.append({
                'title': 'API-First Architecture with Azure API Management',
                'description': 'Centralize and modernize API management',
                'services': [],
                'tech_stack': [
                    'Azure API Management',
                    'Azure Functions',
                    'OpenAPI/Swagger',
                    'OAuth 2.0 / Azure AD'
                ],
                'priority': 'Medium',
                'effort': 8,
                'benefits': [
                    'Centralized API governance',
                    'Rate limiting and throttling',
                    'Developer portal',
                    'Analytics and monitoring'
                ]
            })
        
        # Recommendation 4: Data modernization
        db_chunks = [c for c in chunks if getattr(c, 'language', '') in ['sql', 'plsql', 'tsql']]
        
        if db_chunks:
            recommendations.append({
                'title': 'Data Platform Modernization',
                'description': 'Migrate to modern cloud database services',
                'services': [],
                'tech_stack': [
                    'Azure SQL Database',
                    'Azure Cosmos DB (NoSQL)',
                    'Azure Synapse Analytics (Data Warehouse)',
                    'Azure Data Factory (ETL)'
                ],
                'priority': 'Medium',
                'effort': 10,
                'benefits': [
                    'Managed service (no patching)',
                    'Automatic backups',
                    'Point-in-time restore',
                    'Advanced threat protection'
                ]
            })
        
        # Recommendation 5: DevOps transformation
        recommendations.append({
            'title': 'DevOps and CI/CD Pipeline',
            'description': 'Implement automated build, test, and deployment',
            'services': [],
            'tech_stack': [
                'Azure DevOps / GitHub Actions',
                'Docker containers',
                'Infrastructure as Code (Terraform/Bicep)',
                'Azure Monitor'
            ],
            'priority': 'High',
            'effort': 6,
            'benefits': [
                'Faster time to market',
                'Reduced deployment errors',
                'Automated testing',
                'Version control for infrastructure'
            ]
        })
        
        return recommendations
    
    def _identify_microservice_candidates(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Identify potential microservices from code structure"""
        candidates = []
        
        # Group by module/domain
        modules = defaultdict(list)
        for chunk in chunks:
            file_path = getattr(chunk, 'file_path', '')
            if '/' in file_path:
                module = file_path.split('/')[0]
                modules[module].append(chunk)
        
        # Analyze each module
        for module_name, module_chunks in modules.items():
            # Skip small modules
            if len(module_chunks) < 5:
                continue
            
            # Determine if it's a good service candidate
            reasons = []
            
            # Check for independent data
            has_models = any('model' in getattr(c, 'file_path', '').lower() for c in module_chunks)
            if has_models:
                reasons.append('Independent data model')
            
            # Check for API endpoints
            has_controllers = any('controller' in getattr(c, 'file_path', '').lower() for c in module_chunks)
            if has_controllers:
                reasons.append('Has API endpoints')
            
            # Check for business logic
            has_services = any('service' in getattr(c, 'file_path', '').lower() for c in module_chunks)
            if has_services:
                reasons.append('Distinct business logic')
            
            if len(reasons) >= 2:
                candidates.append({
                    'name': f'{module_name.title()} Service',
                    'description': ', '.join(reasons),
                    'files': len(module_chunks)
                })
        
        return candidates[:5]  # Top 5 candidates
    
    # ==================== TECH STACK ANALYSIS ====================
    
    def analyze_tech_stack(self, chunks: List[Any]) -> Dict[str, Any]:
        """Analyze technology stack used in the project"""
        languages = Counter()
        frameworks = set()
        databases = set()
        cloud_services = set()
        
        for chunk in chunks:
            language = getattr(chunk, 'language', '')
            content = getattr(chunk, 'content', '').lower()
            file_path = getattr(chunk, 'file_path', '').lower()
            
            # Count languages
            if language:
                languages[language] += 1
            
            # Detect frameworks
            framework_patterns = {
                'react': r'import.*react',
                'angular': r'@angular',
                'vue': r'import.*vue',
                'express': r'express\(',
                'django': r'from django',
                'flask': r'from flask',
                '.net': r'using System|namespace \w+',
                'spring': r'@SpringBoot|import org.springframework'
            }
            
            for framework, pattern in framework_patterns.items():
                if re.search(pattern, content):
                    frameworks.add(framework.title())
            
            # Detect databases
            db_keywords = {
                'SQL Server': ['sql server', 'mssql', 'tsql'],
                'PostgreSQL': ['postgresql', 'postgres', 'psql'],
                'MySQL': ['mysql', 'mariadb'],
                'MongoDB': ['mongodb', 'mongoose'],
                'Oracle': ['oracle', 'plsql'],
                'Redis': ['redis'],
                'Elasticsearch': ['elasticsearch']
            }
            
            for db_name, keywords in db_keywords.items():
                if any(kw in content or kw in file_path for kw in keywords):
                    databases.add(db_name)
            
            # Detect cloud services
            cloud_keywords = {
                'Azure': ['azure', 'microsoft.azure'],
                'AWS': ['aws', 'amazon.aws', 'boto3'],
                'Google Cloud': ['google.cloud', 'gcp'],
                'Heroku': ['heroku'],
                'Vercel': ['vercel']
            }
            
            for cloud, keywords in cloud_keywords.items():
                if any(kw in content for kw in keywords):
                    cloud_services.add(cloud)
        
        # Get top languages
        top_languages = [
            {'language': lang, 'file_count': count}
            for lang, count in languages.most_common(5)
        ]
        
        return {
            'languages': top_languages,
            'frameworks': list(frameworks),
            'databases': list(databases),
            'cloud_services': list(cloud_services) if cloud_services else ['On-Premise'],
            'total_files': len(chunks)
        }
    
    # ==================== DEFAULT INSIGHTS ====================
    
    def _get_default_insights(self) -> Dict[str, Any]:
        """Return default insights when analysis fails"""
        return {
            'code_hotspots': [
                {
                    'name': 'Unable to analyze',
                    'complexity': 0,
                    'files': 0,
                    'lines': 0,
                    'issues': ['Analysis error occurred']
                }
            ],
            'db_optimizations': [
                {
                    'type': 'info',
                    'title': 'Analysis unavailable',
                    'impact': 'Unable to generate database recommendations',
                    'recommendation': 'Review database schema manually'
                }
            ],
            'modernization_recommendations': [
                {
                    'title': 'General Modernization',
                    'description': 'Consider cloud migration',
                    'services': [],
                    'tech_stack': ['Azure', 'Kubernetes', 'Docker'],
                    'priority': 'Medium',
                    'effort': 12
                }
            ],
            'tech_stack': {
                'languages': [],
                'frameworks': [],
                'databases': [],
                'cloud_services': ['Unknown'],
                'total_files': 0
            }
        }
