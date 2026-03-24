"""
Quality Service - Document Validation and Quality Scoring
Validates generated documents and assigns quality scores
"""

from typing import Dict, Any, List
import json
import logging
import re

logger = logging.getLogger(__name__)


class QualityService:
    """Service for validating documents and calculating quality scores"""
    
    def __init__(self):
        self.validation_rules = {
            'brd': self._validate_brd,
            'frd': self._validate_frd,
            'user_stories': self._validate_user_stories,
            'test_cases': self._validate_test_cases,
            'migration_plan': self._validate_migration_plan,
            'reverse_eng': self._validate_reverse_eng,
            'tdd': self._validate_tdd,
            'db_analysis': self._validate_db_analysis
        }
    
    def validate_document(
        self, 
        document: Any, 
        project_id: str,
        analysis_type: str
    ) -> float:
        """
        Validate document and return quality score (0-100)
        
        Args:
            document: Document content (dict or str)
            project_id: Project ID for context
            analysis_type: Type of analysis
            
        Returns:
            Quality score 0-100
        """
        try:
            # Parse document if string
            if isinstance(document, str):
                try:
                    doc_content = json.loads(document)
                except:
                    doc_content = {"raw_output": document}
            else:
                doc_content = document
            
            # Get validation function
            validate_func = self.validation_rules.get(analysis_type)
            if not validate_func:
                logger.warning(f"No validation rules for {analysis_type}")
                return 50.0  # Default score
            
            # Run validation
            score = validate_func(doc_content, project_id)
            
            logger.info(f"Quality score for {analysis_type}: {score}")
            return score
            
        except Exception as e:
            logger.error(f"Error validating document: {str(e)}")
            return 50.0
    
    # ==================== VALIDATION METHODS ====================
    
    def _validate_brd(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Business Requirements Document"""
        score = 0.0
        max_score = 100.0
        
        # Check for required sections (50 points)
        required_sections = [
            'executive_summary',
            'business_objectives',
            'scope',
            'functional_requirements',
            'non_functional_requirements'
        ]
        
        content = doc.get('content', doc)
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 50
        
        # Check content quality (30 points)
        # - Each section has meaningful content (not empty or too short)
        quality_points = 0
        for section in required_sections:
            if section in content:
                section_content = str(content[section])
                if len(section_content) > 100:  # At least 100 chars
                    quality_points += 6
        score += quality_points
        
        # Check for specificity (20 points)
        # - References to actual system/code
        # - Specific numbers/metrics
        full_text = json.dumps(content).lower()
        specificity = 0
        
        if any(word in full_text for word in ['user', 'system', 'application', 'process']):
            specificity += 5
        if re.search(r'\d+', full_text):  # Contains numbers
            specificity += 5
        if any(word in full_text for word in ['must', 'shall', 'should', 'will']):
            specificity += 5
        if len(full_text) > 2000:  # Substantial content
            specificity += 5
        
        score += specificity
        
        return min(score, max_score)
    
    def _validate_frd(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Functional Requirements Document"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Required sections (40 points)
        required_sections = [
            'introduction',
            'system_overview',
            'functional_requirements',
            'data_requirements'
        ]
        
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 40
        
        # Check functional requirements structure (40 points)
        if 'functional_requirements' in content:
            reqs = content['functional_requirements']
            if isinstance(reqs, list):
                # Check for structured requirements
                has_ids = any('id' in r or 'ID' in r for r in reqs if isinstance(r, dict))
                has_descriptions = any('description' in r for r in reqs if isinstance(r, dict))
                has_acceptance = any('acceptance' in str(r).lower() for r in reqs if isinstance(r, dict))
                
                if has_ids:
                    score += 15
                if has_descriptions:
                    score += 15
                if has_acceptance:
                    score += 10
        
        # Content depth (20 points)
        full_text = json.dumps(content)
        if len(full_text) > 3000:
            score += 20
        elif len(full_text) > 1500:
            score += 10
        
        return min(score, max_score)
    
    def _validate_user_stories(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate User Stories"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Check if it's a list of stories (20 points)
        stories = content if isinstance(content, list) else content.get('stories', [])
        
        if isinstance(stories, list) and len(stories) > 0:
            score += 20
        
        # Validate story structure (60 points)
        if isinstance(stories, list):
            valid_stories = 0
            for story in stories[:20]:  # Check first 20 stories
                if not isinstance(story, dict):
                    continue
                
                story_score = 0
                
                # Has story format "As a ... I want ... so that ..."
                story_text = str(story.get('story', ''))
                if 'as a' in story_text.lower() and 'i want' in story_text.lower():
                    story_score += 1
                
                # Has acceptance criteria
                if 'acceptance' in str(story).lower():
                    story_score += 1
                
                # Has priority
                if 'priority' in story:
                    story_score += 0.5
                
                if story_score >= 2:
                    valid_stories += 1
            
            score += (valid_stories / min(len(stories), 20)) * 60
        
        # Quantity (20 points)
        if len(stories) >= 15:
            score += 20
        elif len(stories) >= 10:
            score += 15
        elif len(stories) >= 5:
            score += 10
        
        return min(score, max_score)
    
    def _validate_test_cases(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Test Cases"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        test_cases = content if isinstance(content, list) else content.get('test_cases', [])
        
        # Has test cases (20 points)
        if isinstance(test_cases, list) and len(test_cases) > 0:
            score += 20
        
        # Validate test case structure (60 points)
        if isinstance(test_cases, list):
            valid_tests = 0
            for test in test_cases[:20]:
                if not isinstance(test, dict):
                    continue
                
                test_score = 0
                
                # Has test steps
                if 'steps' in test or 'test_steps' in test:
                    test_score += 1
                
                # Has expected results
                if 'expected' in str(test).lower():
                    test_score += 1
                
                # Has test data
                if 'data' in test or 'test_data' in test:
                    test_score += 0.5
                
                if test_score >= 1.5:
                    valid_tests += 1
            
            score += (valid_tests / min(len(test_cases), 20)) * 60
        
        # Quantity (20 points)
        if len(test_cases) >= 15:
            score += 20
        elif len(test_cases) >= 10:
            score += 10
        
        return min(score, max_score)
    
    def _validate_migration_plan(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Migration Plan"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Required sections (50 points)
        required_sections = [
            'assessment', 'strategy', 'phases', 'technical_approach', 'risks'
        ]
        
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 50
        
        # Check for phases (30 points)
        if 'phases' in content:
            phases = content['phases']
            if isinstance(phases, list) and len(phases) >= 3:
                score += 30
            elif isinstance(phases, dict):
                score += 20
        
        # Check for Azure/cloud references (20 points)
        full_text = json.dumps(content).lower()
        if 'azure' in full_text or 'cloud' in full_text:
            score += 10
        if 'migration' in full_text:
            score += 10
        
        return min(score, max_score)
    
    def _validate_reverse_eng(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Reverse Engineering Document"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Required sections (60 points)
        required_sections = [
            'system_overview', 'component_architecture', 
            'data_architecture', 'business_logic'
        ]
        
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 60
        
        # Technical depth (40 points)
        full_text = json.dumps(content).lower()
        
        # Check for technical terms
        tech_terms = ['class', 'function', 'api', 'database', 'component', 'service']
        terms_found = sum(1 for term in tech_terms if term in full_text)
        score += (terms_found / len(tech_terms)) * 20
        
        # Check for code references
        if re.search(r'\.(cs|java|py|js|ts|sql)', full_text):
            score += 20
        
        return min(score, max_score)
    
    def _validate_tdd(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Technical Design Document"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Required sections (50 points)
        required_sections = [
            'system_architecture', 'component_design',
            'data_design', 'security_design', 'technology_stack'
        ]
        
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 50
        
        # Technology stack validation (30 points)
        if 'technology_stack' in content:
            stack = content['technology_stack']
            if isinstance(stack, dict):
                # Check for frontend, backend, database mentions
                has_backend = 'backend' in stack or 'server' in str(stack).lower()
                has_frontend = 'frontend' in stack or 'client' in str(stack).lower()
                has_database = 'database' in stack or 'db' in str(stack).lower()
                
                if has_backend:
                    score += 10
                if has_frontend:
                    score += 10
                if has_database:
                    score += 10
        
        # Architecture depth (20 points)
        full_text = json.dumps(content).lower()
        if 'microservice' in full_text or 'architecture' in full_text:
            score += 10
        if len(full_text) > 3000:
            score += 10
        
        return min(score, max_score)
    
    def _validate_db_analysis(self, doc: Dict[str, Any], project_id: str) -> float:
        """Validate Database Analysis"""
        score = 0.0
        max_score = 100.0
        
        content = doc.get('content', doc)
        
        # Required sections (40 points)
        required_sections = [
            'schema_overview', 'table_analysis', 'optimization_recommendations'
        ]
        
        sections_present = sum(1 for section in required_sections if section in content)
        score += (sections_present / len(required_sections)) * 40
        
        # ER diagram presence (30 points)
        full_text = json.dumps(content)
        if 'erDiagram' in full_text or 'er_diagram' in full_text:
            score += 30
        elif 'mermaid' in full_text.lower():
            score += 20
        
        # Database terms (30 points)
        db_terms = ['table', 'column', 'index', 'foreign key', 'primary key', 'relationship']
        terms_found = sum(1 for term in db_terms if term in full_text.lower())
        score += (terms_found / len(db_terms)) * 30
        
        return min(score, max_score)
    
    # ==================== HELPER METHODS ====================
    
    def get_validation_report(
        self,
        document: Any,
        project_id: str,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Get detailed validation report"""
        score = self.validate_document(document, project_id, analysis_type)
        
        # Determine quality level
        if score >= 80:
            quality_level = "Excellent"
            color = "green"
        elif score >= 60:
            quality_level = "Good"
            color = "blue"
        elif score >= 40:
            quality_level = "Fair"
            color = "yellow"
        else:
            quality_level = "Poor"
            color = "red"
        
        return {
            "score": score,
            "quality_level": quality_level,
            "color": color,
            "analysis_type": analysis_type,
            "validated_at": "utcnow"
        }
