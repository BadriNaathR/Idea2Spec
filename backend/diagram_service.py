"""
Diagram Service - Generate Architecture and ER Diagrams
Uses Mermaid syntax for diagram generation
"""

from typing import List, Dict, Any
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class DiagramService:
    """Service for generating system diagrams"""
    
    def __init__(self):
        pass
    
    # ==================== ARCHITECTURE DIAGRAM ====================
    
    def generate_architecture_diagram(
        self,
        project_id: str,
        chunks: List[Any]
    ) -> str:
        """
        Generate system architecture diagram in Mermaid format
        
        Args:
            project_id: Project ID
            chunks: Document chunks from codebase
            
        Returns:
            Mermaid diagram syntax
        """
        try:
            # Analyze code to identify components
            components = self._identify_components(chunks)
            
            # Generate Mermaid flowchart
            diagram = "graph TB\n"
            diagram += "    %% System Architecture Diagram\n\n"
            
            # Add client layer
            diagram += "    Client[\"👤 Client Applications\"]\n"
            diagram += "    style Client fill:#e1f5ff\n\n"
            
            # Add API Gateway if applicable
            if any('api' in c['name'].lower() or 'controller' in c['name'].lower() for c in components):
                diagram += "    Gateway[\"🚪 API Gateway\"]\n"
                diagram += "    Client --> Gateway\n"
                diagram += "    style Gateway fill:#fff4e1\n\n"
            
            # Add application components
            backend_components = [c for c in components if c['type'] == 'backend']
            frontend_components = [c for c in components if c['type'] == 'frontend']
            
            if frontend_components:
                diagram += "    subgraph Frontend\n"
                for comp in frontend_components[:5]:  # Limit to 5
                    comp_id = comp['name'].replace(' ', '_').replace('.', '_')
                    diagram += f"        {comp_id}[\"{comp['name']}\"]\n"
                diagram += "    end\n"
                diagram += "    style Frontend fill:#f0f0f0\n\n"
                diagram += "    Client --> Frontend\n\n"
            
            if backend_components:
                diagram += "    subgraph Backend[\"Application Layer\"]\n"
                for comp in backend_components[:8]:  # Limit to 8
                    comp_id = comp['name'].replace(' ', '_').replace('.', '_')
                    icon = self._get_component_icon(comp['name'])
                    diagram += f"        {comp_id}[\"{icon} {comp['name']}\"]\n"
                diagram += "    end\n"
                diagram += "    style Backend fill:#e8f5e9\n\n"
                
                if 'Gateway' in diagram:
                    diagram += f"    Gateway --> Backend\n\n"
                else:
                    diagram += f"    Client --> Backend\n\n"
            
            # Add database layer
            db_components = [c for c in components if c['type'] == 'database']
            if db_components or any('database' in c['name'].lower() for c in components):
                diagram += "    DB[(\"🗄️ Database Layer\")]\n"
                diagram += "    Backend --> DB\n"
                diagram += "    style DB fill:#ffebee\n\n"
            
            # Add external services
            external_services = self._identify_external_services(chunks)
            if external_services:
                diagram += "    subgraph External[\"External Services\"]\n"
                for service in external_services[:5]:
                    service_id = service.replace(' ', '_').replace('.', '_')
                    diagram += f"        {service_id}[\"{service}\"]\n"
                diagram += "    end\n"
                diagram += "    Backend --> External\n"
                diagram += "    style External fill:#fff3e0\n\n"
            
            # Add caching if detected
            if any('cache' in c['name'].lower() or 'redis' in str(chunks).lower() for c in components):
                diagram += "    Cache[\"⚡ Cache Layer\"]\n"
                diagram += "    Backend --> Cache\n"
                diagram += "    style Cache fill:#e8eaf6\n\n"
            
            return diagram
            
        except Exception as e:
            logger.error(f"Error generating architecture diagram: {str(e)}")
            return self._get_default_architecture_diagram()
    
    # ==================== ER DIAGRAM ====================
    
    def generate_er_diagram(
        self,
        project_id: str,
        chunks: List[Any]
    ) -> str:
        """
        Generate Entity-Relationship diagram in Mermaid format
        
        Args:
            project_id: Project ID
            chunks: Database-related document chunks
            
        Returns:
            Mermaid ER diagram syntax
        """
        try:
            # Extract entities and relationships
            entities = self._extract_entities(chunks)
            relationships = self._extract_relationships(chunks)
            
            # Generate Mermaid ER diagram
            diagram = "erDiagram\n"
            diagram += "    %% Entity-Relationship Diagram\n\n"
            
            # Add entities with attributes
            for entity in entities:
                diagram += f"    {entity['name']} {{\n"
                
                for attr in entity['attributes'][:10]:  # Limit attributes
                    attr_type = attr.get('type', 'string')
                    attr_name = attr.get('name', 'field')
                    is_pk = attr.get('is_primary_key', False)
                    is_fk = attr.get('is_foreign_key', False)
                    
                    if is_pk:
                        diagram += f"        {attr_type} {attr_name} PK\n"
                    elif is_fk:
                        diagram += f"        {attr_type} {attr_name} FK\n"
                    else:
                        diagram += f"        {attr_type} {attr_name}\n"
                
                diagram += "    }\n\n"
            
            # Add relationships
            for rel in relationships:
                from_entity = rel['from']
                to_entity = rel['to']
                relationship_type = rel['type']
                label = rel.get('label', '')
                
                # Convert relationship type to Mermaid syntax
                if relationship_type == '1:1':
                    mermaid_rel = '||--||'
                elif relationship_type == '1:N':
                    mermaid_rel = '||--o{'
                elif relationship_type == 'N:M':
                    mermaid_rel = '}o--o{'
                else:
                    mermaid_rel = '||--||'
                
                diagram += f"    {from_entity} {mermaid_rel} {to_entity} : \"{label}\"\n"
            
            diagram += "\n"
            
            return diagram
            
        except Exception as e:
            logger.error(f"Error generating ER diagram: {str(e)}")
            return self._get_default_er_diagram()
    
    # ==================== HELPER METHODS ====================
    
    def _identify_components(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Identify system components from code"""
        components = []
        seen_names = set()
        
        for chunk in chunks:
            file_path = getattr(chunk, 'file_path', '')
            language = getattr(chunk, 'language', '')
            content = getattr(chunk, 'content', '')
            
            # Determine component type
            comp_type = 'backend'
            if any(ext in file_path.lower() for ext in ['.jsx', '.tsx', '.vue', '.html', '.css']):
                comp_type = 'frontend'
            elif any(ext in file_path.lower() for ext in ['.sql', '.db']):
                comp_type = 'database'
            
            # Extract component name from file path
            if '/' in file_path:
                parts = file_path.split('/')
                # Look for meaningful directory names
                for part in parts:
                    if part and not part.startswith('.') and part not in ['src', 'main', 'app']:
                        name = part.replace('_', ' ').replace('-', ' ').title()
                        if name not in seen_names and len(name) > 2:
                            components.append({
                                'name': name,
                                'type': comp_type,
                                'file_path': file_path
                            })
                            seen_names.add(name)
                            break
            
            # Also try to extract from class names
            if language in ['csharp', 'java', 'python']:
                class_matches = re.findall(r'class\s+([A-Z][a-zA-Z0-9_]+)', content)
                for class_name in class_matches[:2]:  # Limit per file
                    if class_name not in seen_names:
                        # Infer type from class name
                        if any(suffix in class_name for suffix in ['Controller', 'Service', 'Repository', 'Manager']):
                            comp_type = 'backend'
                        elif any(suffix in class_name for suffix in ['Component', 'View', 'Page']):
                            comp_type = 'frontend'
                        
                        components.append({
                            'name': class_name,
                            'type': comp_type,
                            'file_path': file_path
                        })
                        seen_names.add(class_name)
        
        # Limit total components
        return components[:20]
    
    def _identify_external_services(self, chunks: List[Any]) -> List[str]:
        """Identify external service integrations"""
        services = set()
        
        # Common external services
        service_keywords = {
            'stripe': 'Payment (Stripe)',
            'paypal': 'Payment (PayPal)',
            'twilio': 'SMS (Twilio)',
            'sendgrid': 'Email (SendGrid)',
            'aws': 'AWS Services',
            'azure': 'Azure Services',
            'google': 'Google Services',
            'firebase': 'Firebase',
            'auth0': 'Auth0',
            'oauth': 'OAuth Provider',
            'smtp': 'Email Server',
            'ldap': 'LDAP Directory',
            'redis': 'Redis Cache',
            'elasticsearch': 'Elasticsearch',
            'mongodb': 'MongoDB'
        }
        
        for chunk in chunks:
            content = getattr(chunk, 'content', '').lower()
            
            for keyword, service_name in service_keywords.items():
                if keyword in content and service_name not in services:
                    services.add(service_name)
        
        return list(services)
    
    def _extract_entities(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Extract database entities from SQL or ORM code"""
        entities = []
        seen_entities = set()
        
        for chunk in chunks:
            content = getattr(chunk, 'content', '')
            language = getattr(chunk, 'language', '')
            
            # SQL table detection
            if language in ['sql', 'plsql', 'tsql']:
                # Match CREATE TABLE statements
                table_matches = re.findall(
                    r'CREATE\s+TABLE\s+(?:\w+\.)?(\w+)\s*\((.*?)\)',
                    content,
                    re.IGNORECASE | re.DOTALL
                )
                
                for table_name, columns_str in table_matches:
                    if table_name not in seen_entities:
                        attributes = self._parse_sql_columns(columns_str)
                        entities.append({
                            'name': table_name,
                            'attributes': attributes
                        })
                        seen_entities.add(table_name)
            
            # ORM model detection (Python, C#, Java)
            elif language in ['python', 'csharp', 'java']:
                # Look for class definitions that might be entities
                class_matches = re.findall(
                    r'class\s+([A-Z][a-zA-Z0-9_]+).*?(?:Model|Entity|Table)',
                    content,
                    re.IGNORECASE
                )
                
                for class_name in class_matches:
                    if class_name not in seen_entities:
                        # Extract properties/fields
                        attributes = self._parse_orm_properties(content, class_name)
                        entities.append({
                            'name': class_name,
                            'attributes': attributes
                        })
                        seen_entities.add(class_name)
        
        return entities[:15]  # Limit entities
    
    def _parse_sql_columns(self, columns_str: str) -> List[Dict[str, Any]]:
        """Parse SQL column definitions"""
        attributes = []
        
        # Split by comma (simple parser)
        column_defs = columns_str.split(',')
        
        for col_def in column_defs[:15]:  # Limit columns
            col_def = col_def.strip()
            
            # Extract column name and type
            parts = col_def.split()
            if len(parts) >= 2:
                col_name = parts[0].strip('`"[]')
                col_type = parts[1].upper()
                
                is_pk = 'PRIMARY KEY' in col_def.upper()
                is_fk = 'FOREIGN KEY' in col_def.upper() or 'REFERENCES' in col_def.upper()
                
                attributes.append({
                    'name': col_name,
                    'type': col_type,
                    'is_primary_key': is_pk,
                    'is_foreign_key': is_fk
                })
        
        return attributes
    
    def _parse_orm_properties(self, content: str, class_name: str) -> List[Dict[str, Any]]:
        """Parse ORM model properties"""
        attributes = []
        
        # Simple property extraction (Python/C# style)
        property_matches = re.findall(
            r'(?:public\s+)?(\w+)\s+(\w+)\s*[{;]',
            content
        )
        
        for prop_type, prop_name in property_matches[:15]:
            if prop_name.lower() not in ['class', 'public', 'private', 'protected']:
                attributes.append({
                    'name': prop_name,
                    'type': prop_type,
                    'is_primary_key': 'id' in prop_name.lower() and len(attributes) == 0,
                    'is_foreign_key': prop_name.lower().endswith('id') and len(prop_name) > 2
                })
        
        return attributes
    
    def _extract_relationships(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Extract entity relationships"""
        relationships = []
        
        for chunk in chunks:
            content = getattr(chunk, 'content', '')
            
            # Look for FOREIGN KEY constraints
            fk_matches = re.findall(
                r'FOREIGN\s+KEY\s*\((\w+)\)\s+REFERENCES\s+(\w+)',
                content,
                re.IGNORECASE
            )
            
            for col_name, ref_table in fk_matches:
                # Infer relationship type (simplified)
                rel_type = '1:N' if 'id' in col_name.lower() else 'N:M'
                
                relationships.append({
                    'from': 'Current',  # Would need more context
                    'to': ref_table,
                    'type': rel_type,
                    'label': 'has'
                })
        
        return relationships[:20]  # Limit relationships
    
    def _get_component_icon(self, component_name: str) -> str:
        """Get icon for component based on name"""
        name_lower = component_name.lower()
        
        if 'auth' in name_lower:
            return '🔐'
        elif 'user' in name_lower:
            return '👤'
        elif 'payment' in name_lower or 'transaction' in name_lower:
            return '💳'
        elif 'report' in name_lower:
            return '📊'
        elif 'notification' in name_lower or 'email' in name_lower:
            return '📧'
        elif 'file' in name_lower or 'document' in name_lower:
            return '📄'
        elif 'search' in name_lower:
            return '🔍'
        elif 'admin' in name_lower:
            return '⚙️'
        else:
            return '📦'
    
    def _get_default_architecture_diagram(self) -> str:
        """Default architecture diagram when generation fails"""
        return """graph TB
    Client["👤 Client Applications"]
    Gateway["🚪 API Gateway"]
    Backend["📦 Application Layer"]
    DB[("🗄️ Database")]
    Cache["⚡ Cache Layer"]
    
    Client --> Gateway
    Gateway --> Backend
    Backend --> DB
    Backend --> Cache
    
    style Client fill:#e1f5ff
    style Gateway fill:#fff4e1
    style Backend fill:#e8f5e9
    style DB fill:#ffebee
    style Cache fill:#e8eaf6
"""
    
    def _get_default_er_diagram(self) -> str:
        """Default ER diagram when generation fails"""
        return """erDiagram
    USERS {
        int id PK
        string username
        string email
        datetime created_at
    }
    
    PROJECTS {
        int id PK
        string name
        int user_id FK
        datetime created_at
    }
    
    DOCUMENTS {
        int id PK
        int project_id FK
        string content
        datetime created_at
    }
    
    USERS ||--o{ PROJECTS : "creates"
    PROJECTS ||--o{ DOCUMENTS : "contains"
"""
