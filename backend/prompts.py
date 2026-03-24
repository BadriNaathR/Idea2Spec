"""
Prompts Module - Contains all AI prompts for document generation
Separated for maintainability and easy customization
"""

from typing import Dict, List, Any


def get_detailed_prompts(analysis_type: str, project_name: str, domain: str, code_summary: str, supporting_knowledge: str = "", user_stories_context: str = "") -> List[Dict]:

    PROFESSIONAL_PREAMBLE = """LANGUAGE DIRECTIVE: You are generating formal enterprise documentation.
Use professional, neutral business and technical language throughout.
Always write as a senior enterprise consultant producing client-facing documentation.

"""
    
    # Split SME feedback out of supporting_knowledge if present (it's prepended with the mandatory header)
    sme_block = ""
    clean_knowledge = supporting_knowledge
    sme_marker = "================================================================================\nSME / PRODUCT OWNER MANDATORY FEEDBACK"
    if supporting_knowledge and sme_marker in supporting_knowledge:
        # Put SME block first, rest of knowledge after
        parts = supporting_knowledge.split("\n\n", 1)
        sme_block = supporting_knowledge  # keep full block as-is for top placement
        clean_knowledge = ""  # already included in sme_block

    # Build knowledge section
    knowledge_section = ""
    if clean_knowledge and clean_knowledge.strip():
        knowledge_section = f"""

SUPPORTING KNOWLEDGE & BUSINESS CONTEXT:
{clean_knowledge}

---"""

    # Inject confirmed user stories
    user_stories_section = ""
    if user_stories_context and user_stories_context.strip() and analysis_type != "user_stories":
        user_stories_section = f"""

CONFIRMED USER STORIES (PRIMARY GROUNDING — MUST align all content with these):
The following user stories have been reviewed and confirmed by the SME/Product Owner.
Every requirement, test case, design decision, and recommendation you generate MUST directly
trace back to one or more of these user stories. Do not introduce features or requirements
that are not represented in these stories.

{user_stories_context}

---"""

    # SME feedback goes FIRST so the LLM sees it before anything else
    sme_section = f"{sme_block}\n" if sme_block else ""

    base_context = f"""{sme_section}PROJECT: {project_name}
DOMAIN: {domain}
{knowledge_section}{user_stories_section}
CODE ANALYSIS:
{code_summary}"""
    
    prompts = {
        'brd': _get_brd_prompts(base_context),
        'frd': _get_frd_prompts(base_context),
        'user_stories': _get_user_stories_prompts(base_context),
        'test_cases': _get_test_cases_prompts(base_context),
        'migration_plan': _get_migration_plan_prompts(base_context),
        'reverse_eng': _get_reverse_eng_prompts(base_context),
        'tdd': _get_tdd_prompts(base_context),
        'db_analysis': _get_db_analysis_prompts(base_context),
    }

    result = prompts.get(analysis_type, prompts['brd'])
    # Prepend professional language preamble to every prompt step
    for step in result:
        step['prompt'] = PROFESSIONAL_PREAMBLE + step['prompt']
    return result


def get_prompt_metadata(analysis_type: str) -> Dict[str, Any]:
    """
    Get metadata about prompts for a given analysis type.
    Used for progress tracking and ETA estimation.
    
    Returns:
        Dictionary with step_count, estimated_time_per_step, section_names
    """
    metadata = {
        'brd': {
            'step_count': 10,
            'estimated_seconds_per_step': 45,
            'section_names': [
                'Executive Summary',
                'Business Objectives', 
                'Scope',
                'Functional Requirements',
                'Non-Functional Requirements',
                'User Requirements',
                'System Requirements',
                'Data Requirements',
                'Constraints and Assumptions',
                'Appendices'
            ]
        },
        'frd': {
            'step_count': 6,
            'estimated_seconds_per_step': 50,
            'section_names': [
                'Introduction',
                'System Overview',
                'Functional Requirements',
                'Data Requirements',
                'Interface Requirements',
                'Security Requirements'
            ]
        },
        'user_stories': {
            'step_count': 4,
            'estimated_seconds_per_step': 60,
            'section_names': [
                'Epics Overview',
                'User Stories (Set 1)',
                'User Stories (Set 2)',
                'Story Mapping'
            ]
        },
        'test_cases': {
            'step_count': 5,
            'estimated_seconds_per_step': 55,
            'section_names': [
                'Test Strategy',
                'Functional Test Cases',
                'Negative Test Cases',
                'Integration Test Cases',
                'Performance Test Cases'
            ]
        },
        'migration_plan': {
            'step_count': 5,
            'estimated_seconds_per_step': 50,
            'section_names': [
                'Executive Summary',
                'Current State Analysis',
                'Target State Design',
                'Migration Phases',
                'Risk and Rollback'
            ]
        },
        'reverse_eng': {
            'step_count': 5,
            'estimated_seconds_per_step': 45,
            'section_names': [
                'System Overview',
                'Architecture Analysis',
                'Technology Stack',
                'Data Model',
                'Technical Debt'
            ]
        },
        'tdd': {
            'step_count': 6,
            'estimated_seconds_per_step': 50,
            'section_names': [
                'Technical Overview',
                'Architecture Design',
                'Data Design',
                'API Design',
                'Security Design',
                'Deployment Design'
            ]
        },
        'db_analysis': {
            'step_count': 4,
            'estimated_seconds_per_step': 40,
            'section_names': [
                'Database Overview',
                'Schema Analysis',
                'Index Analysis',
                'Optimization Recommendations'
            ]
        }
    }
    
    return metadata.get(analysis_type, metadata['brd'])


# ==================== BRD PROMPTS ====================

def _get_brd_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'executive_summary',
            'prompt': f"""You are a Senior Business Analyst creating a comprehensive Business Requirements Document that will be 40+ pages.

{base_context}

IMPORTANT: Base this BRD on the CONFIRMED USER STORIES provided above. Every business objective, capability, and requirement must trace to at least one user story.

Generate an EXTREMELY DETAILED EXECUTIVE SUMMARY section (target: 3-4 pages worth of content). Include:

1. **Document Purpose and Overview** (2-3 paragraphs):
   - What is this application and why does it exist?
   - Historical context and evolution
   - Strategic importance to the organization

2. **Business Context and Value Proposition** (3-4 paragraphs):
   - Detailed business value and ROI justification
   - Cost-benefit analysis considerations
   - Competitive advantages provided
   - Market positioning implications

3. **Target Audience and Stakeholders** (comprehensive list with detailed descriptions):
   - Primary users (with demographics, needs, pain points)
   - Secondary users
   - System administrators
   - Business stakeholders
   - Technical stakeholders
   - External parties (partners, vendors, regulators)

4. **Key Capabilities and Features** (10-15 capabilities with full descriptions):
   - Core functionality with detailed explanations
   - Supporting features
   - Integration capabilities
   - Reporting and analytics capabilities
   - Security and compliance features

5. **Success Metrics and KPIs** (10+ metrics):
   - Business metrics (revenue, cost savings, efficiency)
   - User metrics (adoption, satisfaction, engagement)
   - Technical metrics (performance, availability, quality)
   - Operational metrics (support tickets, training time)

6. **Project Vision Statement**: A compelling 2-3 sentence vision

Return as comprehensive JSON with all fields filled with detailed content."""
        },
        {
            'section': 'business_objectives',
            'prompt': f"""You are a Senior Business Analyst continuing the Business Requirements Document.

{base_context}

CRITICAL: Every objective below MUST map directly to one or more user stories from the CONFIRMED USER STORIES section above. Reference the story IDs (US-XXX) explicitly.

Generate detailed BUSINESS OBJECTIVES with:
1. **Primary Objectives**: Main business goals (5-7 with detailed descriptions)
2. **Secondary Objectives**: Supporting goals
3. **Strategic Alignment**: How does this align with business strategy?
4. **Problem Statement**: What problems does this solve? (detailed)
5. **Expected Outcomes**: Measurable outcomes with timelines

Return as JSON:
{{"primary_objectives": [{{"id": "BO-001", "objective": "title", "description": "detailed desc", "priority": "Critical/High/Medium", "success_criteria": "how measured"}}], "secondary_objectives": [...], "strategic_alignment": "text", "problem_statement": "detailed text", "expected_outcomes": [{{"outcome": "name", "timeline": "when", "measurement": "how"}}]}}"""
        },
        {
            'section': 'scope',
            'prompt': f"""You are a Senior Business Analyst continuing the Business Requirements Document.

{base_context}

CRITICAL: The in-scope features MUST be derived exclusively from the CONFIRMED USER STORIES above. Each in-scope item should reference the US-XXX story it comes from. Do not include features not represented in those stories.

Generate detailed SCOPE section with:
1. **In-Scope Features**: Detailed list of what's included (10+ items with descriptions)
2. **Out-of-Scope Items**: What's explicitly excluded and why
3. **Boundaries**: System boundaries and interfaces
4. **Phases**: If phased approach, define phases
5. **Dependencies**: External dependencies and assumptions

Return as JSON:
{{"in_scope": [{{"feature": "name", "description": "detailed", "priority": "P1/P2/P3", "phase": 1}}], "out_of_scope": [{{"item": "name", "reason": "why excluded"}}], "boundaries": [{{"boundary": "name", "description": "desc"}}], "phases": [{{"phase": 1, "name": "name", "scope": "what included", "duration": "estimate"}}], "dependencies": [{{"dependency": "name", "type": "internal/external", "impact": "desc"}}]}}"""
        },
        {
            'section': 'functional_requirements',
            'prompt': f"""You are a Senior Business Analyst creating comprehensive functional requirements.

{base_context}

IMPORTANT: Each functional requirement MUST trace to one or more user stories from the CONFIRMED USER STORIES above. Include the story ID (e.g., US-001) in the "source" field of each requirement. Do not add requirements that have no corresponding user story.

Generate EXTREMELY DETAILED FUNCTIONAL REQUIREMENTS (target: 8-10 pages of content).

Create AT LEAST 30 detailed functional requirements organized by functional area. Each requirement MUST include:

1. **Requirement ID**: FR-XXX format
2. **Title**: Clear, action-oriented title
3. **Description**: 3-5 sentences describing what the system shall do
4. **Rationale**: Why this requirement is needed (business justification)
5. **Acceptance Criteria**: 4-6 detailed Given/When/Then format criteria
6. **Priority**: Must Have / Should Have / Could Have / Won't Have (MoSCoW)
7. **Source**: User Story ID(s) this traces to (e.g., US-001, US-002)
8. **Dependencies**: Related requirements
9. **Assumptions**: Any assumptions made
10. **Constraints**: Any constraints that apply

Organize requirements into these categories:
- User Management (authentication, authorization, profiles)
- Core Business Logic (main application functions)
- Data Management (CRUD operations, data handling)
- Reporting and Analytics
- Integration Requirements
- Workflow and Process Automation
- Notification and Communication
- Search and Navigation
- Configuration and Settings
- Audit and Compliance

Return as JSON with 30+ comprehensive requirements."""
        },
        {
            'section': 'non_functional_requirements',
            'prompt': f"""You are a Senior Business Analyst creating comprehensive non-functional requirements.

{base_context}

Generate EXTREMELY DETAILED NON-FUNCTIONAL REQUIREMENTS (target: 6-8 pages of content).

Cover ALL of the following categories with MULTIPLE requirements each (3-5 per category):

1. **Performance Requirements** (5+ requirements):
   - Response time requirements (by transaction type)
   - Throughput requirements
   - Capacity requirements
   - Resource utilization limits
   - Batch processing performance

2. **Scalability Requirements** (4+ requirements):
   - Horizontal scaling capabilities
   - Vertical scaling limits
   - User growth projections
   - Data growth projections
   - Geographic distribution

3. **Security Requirements** (8+ requirements):
   - Authentication requirements (MFA, SSO, etc.)
   - Authorization and access control
   - Data encryption (at rest and in transit)
   - Session management
   - Input validation and sanitization
   - Audit logging requirements
   - Compliance requirements (GDPR, SOC2, etc.)
   - Security gap remediation management

4. **Reliability and Availability** (5+ requirements):
   - Uptime requirements (SLA)
   - Fault tolerance
   - Disaster recovery
   - Backup and restore
   - Failover capabilities

5. **Usability Requirements** (5+ requirements):
   - Accessibility standards (WCAG)
   - User interface standards
   - Learning curve expectations
   - Error handling and messaging
   - Help and documentation

6. **Maintainability Requirements** (4+ requirements):
   - Code standards and documentation
   - Monitoring and observability
   - Logging standards
   - Configuration management

7. **Compatibility Requirements** (3+ requirements):
   - Browser support
   - Device support
   - Integration standards

Each requirement should have: ID, Title, Detailed Specification, Measurement Method, Target Value.

Return as comprehensive JSON with 30+ non-functional requirements."""
        },
        {
            'section': 'user_requirements',
            'prompt': f"""You are a Senior Business Analyst creating comprehensive user requirements.

{base_context}

Generate EXTREMELY DETAILED USER REQUIREMENTS (target: 6-8 pages of content).

1. **User Personas** (5-7 detailed personas):
   Each persona should include:
   - Name and role title
   - Demographics (age range, tech proficiency, work environment)
   - Goals (primary and secondary, 4-5 each)
   - Pain points and frustrations (5-6 items)
   - Needs and expectations (6-8 items)
   - Typical day/workflow description
   - Key tasks they perform
   - Success criteria for them

2. **User Journeys** (3-5 detailed journeys per persona):
   Each journey should include:
   - Journey name and description
   - Trigger/entry point
   - 8-12 detailed steps with:
     * Step number
     * User action
     * System response
     * Touchpoint (UI element)
     * Emotions/thoughts at this step
     * Potential pain points
   - Success outcome
   - Alternative paths

3. **User Needs Matrix**:
   - Map each need to specific personas
   - Priority (High/Medium/Low)
   - Mapped features/requirements
   - Frequency of need
   - Impact if not met

4. **Accessibility Requirements**:
   - WCAG 2.1 Level AA compliance details
   - Assistive technology support
   - Cognitive accessibility considerations

Return as comprehensive JSON with deeply detailed user requirements."""
        },
        {
            'section': 'system_requirements',
            'prompt': f"""You are a Senior Business Analyst continuing the Business Requirements Document.

{base_context}

Generate detailed SYSTEM REQUIREMENTS covering:
1. **Hardware Requirements**: Servers, storage, network
2. **Software Requirements**: OS, frameworks, databases
3. **Integration Requirements**: APIs, third-party systems
4. **Infrastructure Requirements**: Cloud, on-premise, hybrid

Return as JSON:
{{"hardware": [{{"component": "name", "specification": "spec", "quantity": "n", "purpose": "why"}}], "software": [{{"component": "name", "version": "v", "license": "type", "purpose": "why"}}], "integrations": [{{"system": "name", "type": "API/File/Event", "direction": "inbound/outbound/bidirectional", "data_exchanged": "what data", "frequency": "real-time/batch"}}], "infrastructure": [{{"component": "name", "provider": "AWS/Azure/etc", "configuration": "specs", "redundancy": "HA setup"}}]}}"""
        },
        {
            'section': 'data_requirements',
            'prompt': f"""You are a Senior Business Analyst creating comprehensive data requirements.

{base_context}

Generate EXTREMELY DETAILED DATA REQUIREMENTS (target: 6-8 pages of content).

1. **Data Entities** (15-20 entities):
   Each entity should include:
   - Entity name and description (2-3 sentences)
   - Business purpose
   - 10-15 attributes with:
     * Attribute name
     * Data type and size
     * Required/optional
     * Default value
     * Validation rules
     * Business rules
     * Description
   - Relationships to other entities
   - Primary key and unique constraints
   - Sample data examples

2. **Data Flows** (8-10 data flows):
   Each flow should include:
   - Flow name and description
   - Source system/component
   - Destination system/component
   - Data elements transferred
   - Trigger mechanism
   - Frequency/volume
   - Transformation rules
   - Error handling

3. **Data Governance**:
   - Data classification scheme
   - Retention policies by data type
   - Privacy requirements (GDPR, CCPA)
   - Data ownership matrix
   - Access control requirements
   - Compliance requirements

4. **Data Quality Rules** (15-20 rules):
   - Rule name
   - Applies to which data
   - Validation logic
   - Error handling
   - Remediation process

5. **Master Data Management**:
   - Master data entities
   - Source of truth definitions
   - Synchronization requirements

Return as comprehensive JSON with all data specifications."""
        },
        {
            'section': 'constraints_and_assumptions',
            'prompt': f"""You are a Senior Business Analyst completing the Business Requirements Document.

{base_context}

Generate detailed CONSTRAINTS AND ASSUMPTIONS:
1. **Technical Constraints**: Technology limitations
2. **Business Constraints**: Budget, timeline, resources
3. **Regulatory Constraints**: Compliance requirements
4. **Assumptions**: Things assumed to be true
5. **Risks**: Potential risks with mitigation strategies

Return as JSON:
{{"technical_constraints": [{{"constraint": "name", "description": "detail", "impact": "how it affects project", "mitigation": "workaround"}}], "business_constraints": [...], "regulatory_constraints": [...], "assumptions": [{{"assumption": "text", "basis": "why assumed", "risk_if_wrong": "impact", "validation_approach": "how to validate"}}], "risks": [{{"id": "R-001", "risk": "description", "probability": "High/Medium/Low", "impact": "High/Medium/Low", "mitigation": "strategy", "owner": "who responsible"}}]}}"""
        },
        {
            'section': 'appendices',
            'prompt': f"""You are a Senior Business Analyst completing the Business Requirements Document.

{base_context}

Generate APPENDICES including:
1. **Glossary**: Technical and business terms
2. **Acronyms**: All acronyms used
3. **References**: Related documents and standards
4. **Revision History**: Document versioning
5. **Approval Matrix**: Who needs to approve

Return as JSON:
{{"glossary": [{{"term": "term", "definition": "definition"}}], "acronyms": [{{"acronym": "ABC", "expansion": "full form"}}], "references": [{{"title": "doc name", "type": "Standard/Regulation/Internal", "relevance": "why relevant"}}], "revision_history": [{{"version": "1.0", "date": "YYYY-MM-DD", "author": "Auto-generated", "changes": "Initial draft"}}], "approval_matrix": [{{"role": "Role Name", "responsibility": "Approve/Review/Inform", "name": "TBD"}}]}}"""
        }
    ]


# ==================== FRD PROMPTS ====================

def _get_frd_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'introduction',
            'prompt': f"""You are a Requirements Engineer creating a detailed Functional Requirements Document.

{base_context}

IMPORTANT: This FRD must be grounded in the CONFIRMED USER STORIES above. All functional specifications must trace back to those stories.

Generate a comprehensive INTRODUCTION section with:
1. **Purpose**: Why this document exists (detailed)
2. **Scope**: What this FRD covers
3. **Audience**: Who should read this document
4. **Document Conventions**: How to read requirements
5. **References**: Related documents

Return as JSON with detailed text for each field."""
        },
        {
            'section': 'system_overview',
            'prompt': f"""You are a Requirements Engineer continuing the Functional Requirements Document.

{base_context}

CRITICAL: The system overview MUST reflect the scope defined by the CONFIRMED USER STORIES above. User classes and external interfaces must match the roles and integrations described in those stories.

Generate detailed SYSTEM OVERVIEW with:
1. **System Context**: Where the system fits in the ecosystem
2. **System Architecture**: High-level architecture description
3. **Major Components**: Each component with responsibilities
4. **External Interfaces**: All external system connections
5. **User Classes**: Different types of users

Return as JSON with nested objects for each section."""
        },
        {
            'section': 'functional_requirements',
            'prompt': f"""You are a Requirements Engineer creating detailed functional requirements.

{base_context}

IMPORTANT: Each functional requirement MUST reference the user story ID(s) it implements from the CONFIRMED USER STORIES above. Only generate requirements that are traceable to those stories.

Generate 20+ FUNCTIONAL REQUIREMENTS organized by feature area. Each requirement must have:
- Unique ID (FR-XXX)
- Title
- Detailed Description (2-3 sentences minimum)
- User Story format (As a... I want... So that...)
- Acceptance Criteria (3-5 testable criteria each)
- Priority (Must/Should/Could/Won't)
- User Story Traceability: which US-XXX story/stories this implements
- Dependencies

Return as JSON: {{"feature_areas": [{{"area": "Feature Area Name", "description": "area desc", "requirements": [{{"id": "FR-001", "user_story_ref": "US-001", ...}}]}}]}}"""
        },
        {
            'section': 'data_requirements',
            'prompt': f"""You are a Requirements Engineer documenting data requirements.

{base_context}

Generate detailed DATA REQUIREMENTS:
1. **Data Models**: Entity definitions with all attributes
2. **Validation Rules**: All business rules for data
3. **Data Transformations**: How data changes in the system
4. **Reporting Requirements**: What reports are needed

Return as JSON with comprehensive data specifications."""
        },
        {
            'section': 'interface_requirements',
            'prompt': f"""You are a Requirements Engineer documenting interface requirements.

{base_context}

Generate detailed INTERFACE REQUIREMENTS:
1. **User Interfaces**: Each screen/page with elements
2. **API Interfaces**: All APIs with endpoints, methods, payloads
3. **Hardware Interfaces**: Any hardware integrations
4. **Software Interfaces**: Third-party software integrations

Return as JSON with detailed interface specifications."""
        },
        {
            'section': 'security_requirements',
            'prompt': f"""You are a Requirements Engineer documenting security requirements.

{base_context}

Generate detailed SECURITY REQUIREMENTS:
1. **Authentication**: How users prove identity
2. **Authorization**: How access is controlled
3. **Data Protection**: Encryption, masking, etc.
4. **Audit Trail**: What's logged and how
5. **Compliance**: Regulatory requirements

Return as JSON with detailed security specifications."""
        }
    ]


# ==================== USER STORIES PROMPTS ====================

def _get_user_stories_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'epics_overview',
            'prompt': f"""You are a Product Owner creating comprehensive user stories documentation (target: 40+ pages).

{base_context}

CRITICAL: If SME / PRODUCT OWNER MANDATORY FEEDBACK is present above, you MUST treat every point in it as a hard requirement. Add, modify, or remove epics and stories to fully satisfy that feedback before anything else.

Generate DETAILED EPICS OVERVIEW with 8-12 epics:

Each epic MUST include:
1. **Epic ID**: E-XXX format
2. **Title**: Clear, business-focused title
3. **Description**: 3-4 paragraph description of the epic
4. **Business Value**: Detailed explanation of why this epic matters
5. **User Impact**: How this affects different user types
6. **Success Metrics**: 4-5 measurable outcomes
7. **Dependencies**: Other epics this depends on or enables
8. **Estimated Effort**: T-shirt size (S/M/L/XL) with reasoning
9. **Priority**: Critical/High/Medium/Low with justification
10. **Risks**: Potential risks and mitigation strategies
11. **Assumptions**: Key assumptions made

Return as comprehensive JSON with 8-12 fully detailed epics."""
        },
        {
            'section': 'user_stories_set1',
            'prompt': f"""You are a Product Owner creating detailed user stories.

{base_context}

CRITICAL: If SME / PRODUCT OWNER MANDATORY FEEDBACK is present above, every specific story, flow, or role mentioned in that feedback MUST appear as a dedicated user story in this set. Do not omit any feedback point.

Generate 25-30 DETAILED USER STORIES for core functionality. Each story MUST include:

1. **Story ID**: US-XXX format
2. **Epic Reference**: Which epic this belongs to
3. **Title**: Clear, action-oriented title
4. **User Story**: "As a [specific user type], I want [specific action with details] so that [specific benefit with business value]"
5. **Detailed Description**: 2-3 paragraphs explaining the feature in detail
6. **Acceptance Criteria**: 5-8 detailed Given/When/Then format criteria
7. **Story Points**: 1, 2, 3, 5, 8, 13 with justification
8. **Priority**: Must Have / Should Have / Could Have (MoSCoW)
9. **Dependencies**: Related stories
10. **Technical Notes**: Implementation considerations
11. **UI/UX Considerations**: User interface requirements
12. **Test Scenarios**: Key scenarios to test
13. **Out of Scope**: What's explicitly not included

Focus on:
- User authentication and authorization
- Core business processes
- Data management features
- Primary user workflows

Return as comprehensive JSON array with 25-30 stories."""
        },
        {
            'section': 'user_stories_set2',
            'prompt': f"""You are a Product Owner continuing user story creation.

{base_context}

CRITICAL: If SME / PRODUCT OWNER MANDATORY FEEDBACK is present above, ensure any remaining feedback points not covered in Set 1 are addressed here as explicit user stories.

Generate 25-30 MORE DETAILED USER STORIES for additional functionality. Each story must follow same comprehensive format as before.

Focus on:
- Edge cases and error handling
- Administrative and configuration functions
- Reporting and analytics features
- Integration scenarios
- Notification and communication features
- Search and filtering capabilities
- Bulk operations
- Data import/export
- Audit and compliance features
- Performance optimization features

Return as comprehensive JSON array with 25-30 additional stories."""
        },
        {
            'section': 'story_mapping',
            'prompt': f"""You are a Product Owner creating a comprehensive story map.

{base_context}

Create a DETAILED STORY MAP including:

1. **User Activities** (backbone):
   - 6-8 major user activities across the top
   - Each activity mapped to epics

2. **Release Plan**:
   - MVP (Release 1): Essential stories for go-live
   - Release 2: Important enhancements
   - Release 3: Nice-to-have features
   - Future: Backlog items
   
3. **Story Dependencies**:
   - Dependency chains between stories
   - Blocking relationships
   - Recommended implementation order

4. **Sprint Recommendations**:
   - Suggested sprint groupings
   - Velocity considerations
   - Risk-based prioritization

5. **MVP Definition**:
   - Minimum feature set for launch
   - Justification for each MVP item
   - What's deferred and why

Return as comprehensive JSON with full story mapping details."""
        }
    ]


# ==================== TEST CASES PROMPTS ====================

def _get_test_cases_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'test_strategy',
            'prompt': f"""You are a QA Architect creating a comprehensive test strategy (target: 40+ pages total document).

{base_context}

IMPORTANT: The test strategy and all test cases MUST be derived from the CONFIRMED USER STORIES above. Every test scenario must trace to at least one user story. Use the story IDs (US-XXX) as the basis for test coverage.

Generate an EXTREMELY DETAILED TEST STRATEGY (target: 8-10 pages):

1. **Testing Objectives** (detailed):
   - Primary testing goals
   - Quality metrics to achieve
   - Risk-based testing priorities
   - Coverage targets

2. **Test Levels** (detailed descriptions of each):
   - Unit Testing: scope, tools, coverage targets
   - Integration Testing: approach, scope, patterns
   - System Testing: scope, approach, environment
   - User Acceptance Testing: criteria, process, participants
   - Regression Testing: approach, automation strategy

3. **Test Types** (detailed approach for each):
   - Functional Testing
   - Performance Testing
   - Security Testing
   - Usability Testing
   - Compatibility Testing
   - Accessibility Testing
   - Localization Testing
   - Recovery Testing

4. **Entry/Exit Criteria**:
   - Detailed entry criteria for each test phase
   - Exit criteria with specific metrics
   - Defect thresholds

5. **Test Environment Requirements**:
   - Environment specifications
   - Data requirements
   - Tool requirements
   - Access requirements

6. **Test Data Strategy**:
   - Data generation approach
   - Data masking requirements
   - Test data management

7. **Defect Management**:
   - Severity definitions
   - Priority definitions
   - Defect lifecycle
   - Escalation process

8. **Tools and Infrastructure**:
   - Test management tools
   - Automation frameworks
   - CI/CD integration

Return as comprehensive JSON with full test strategy."""
        },
        {
            'section': 'functional_test_cases',
            'prompt': f"""You are a Senior QA Engineer creating comprehensive functional test cases.

{base_context}

IMPORTANT: Each test case MUST reference the user story ID it validates (from the CONFIRMED USER STORIES above). Include "user_story_ref" field with the US-XXX ID. Generate one or more test cases per user story to ensure full coverage.

Generate 35-40 DETAILED FUNCTIONAL TEST CASES covering all happy path scenarios.

Each test case MUST include:
1. **Test ID**: TC-FUN-XXX format
2. **Title**: Clear, descriptive title
3. **User Story Ref**: US-XXX that this test validates
4. **Description**: 2-3 sentences describing what's being tested
5. **Category**: Which feature/module
6. **Priority**: P1 (Critical) / P2 (High) / P3 (Medium)
7. **Preconditions**: Detailed setup requirements (3-5 items)
8. **Test Data**: Specific test data needed
9. **Test Steps**: 8-12 numbered, detailed steps
10. **Expected Results**: Specific, measurable outcomes for each step
11. **Postconditions**: System state after test
12. **Related Requirements**: Linked to FR-XXX
13. **Automation Candidate**: Yes/No with reason

Return as comprehensive JSON with 35-40 test cases."""
        },
        {
            'section': 'negative_test_cases',
            'prompt': f"""You are a Senior QA Engineer creating comprehensive negative test cases.

{base_context}

Generate 25-30 DETAILED NEGATIVE TEST CASES covering error scenarios.

Focus on:
- Invalid input handling (all field types)
- Boundary conditions (min/max values)
- Database input validation edge cases
- Output encoding edge cases
- Authentication failures
- Authorization violations
- Concurrent user scenarios
- Network failure handling
- Database constraint violations
- File upload edge cases
- Session timeout handling
- Data corruption scenarios
- Integration failure handling

Each test case must follow same comprehensive format as functional tests.

Return as comprehensive JSON with 25-30 negative test cases."""
        },
        {
            'section': 'integration_test_cases',
            'prompt': f"""You are a Senior QA Engineer creating integration test cases.

{base_context}

Generate 20-25 DETAILED INTEGRATION TEST CASES covering:

1. **API Integration Tests** (8-10):
   - Request/response validation
   - Error handling
   - Rate limiting
   - Authentication flows

2. **Database Integration Tests** (5-7):
   - CRUD operations
   - Transaction handling
   - Data integrity
   - Concurrent access

3. **External System Integration Tests** (5-8):
   - Third-party service integration
   - Event handling
   - Message queue testing
   - File transfer testing

Each test must include detailed steps, test data, and expected results.

Return as comprehensive JSON with 20-25 integration test cases."""
        },
        {
            'section': 'performance_test_cases',
            'prompt': f"""You are a Performance QA Engineer creating performance test cases.

{base_context}

Generate COMPREHENSIVE PERFORMANCE TEST SCENARIOS:

1. **Load Test Scenarios** (6-8 scenarios):
   - Normal load simulation
   - Peak load simulation
   - User profile definitions
   - Transaction mix
   - Think times
   - Ramp-up strategy
   - Success criteria

2. **Stress Test Scenarios** (4-5 scenarios):
   - Breaking point identification
   - Resource exhaustion testing
   - Recovery testing

3. **Endurance Test Scenarios** (3-4 scenarios):
   - Memory leak detection
   - Long-running stability
   - Database growth impact

4. **Spike Test Scenarios** (3-4 scenarios):
   - Sudden load increase
   - Recovery time measurement

5. **Scalability Test Scenarios** (3-4 scenarios):
   - Horizontal scaling verification
   - Vertical scaling limits

For each scenario include:
- Scenario description
- User load profile
- Duration
- Measurements to collect
- Acceptance criteria with specific thresholds
- Infrastructure requirements

Return as comprehensive JSON with all performance test scenarios."""
        }
    ]


# ==================== MIGRATION PLAN PROMPTS ====================

def _get_migration_plan_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'executive_summary',
            'prompt': f"""You are a Migration Architect creating a comprehensive migration plan (target: 40+ pages).

{base_context}

IMPORTANT: The migration plan must ensure all CONFIRMED USER STORIES above are fully supported in the target state. Reference story IDs when describing capabilities that must be preserved or modernized.

Generate an EXTREMELY DETAILED EXECUTIVE SUMMARY (target: 4-5 pages):

1. **Migration Overview** (2-3 paragraphs):
   - Purpose of migration
   - Strategic drivers
   - Expected outcomes

2. **Scope Summary**:
   - Systems in scope (detailed list)
   - Data volumes to migrate
   - Users impacted
   - Integrations affected

3. **Timeline Overview**:
   - Major milestones
   - Phase durations
   - Go-live target

4. **Investment Summary**:
   - Resource requirements
   - Infrastructure costs
   - Tool/license costs
   - Risk contingency

5. **Key Stakeholders**:
   - Executive sponsors
   - Business owners
   - Technical leads
   - End user representatives

6. **Critical Success Factors**:
   - Technical success criteria
   - Business success criteria
   - Go/No-Go criteria

7. **Risk Summary**:
   - Top 5 risks with mitigation approach
   - Contingency plans

Return as comprehensive JSON."""
        },
        {
            'section': 'current_state_analysis',
            'prompt': f"""You are a Migration Architect analyzing the current state.

{base_context}

Generate EXTREMELY DETAILED CURRENT STATE ANALYSIS (target: 8-10 pages):

1. **System Inventory** (comprehensive list):
   - All applications and versions
   - Databases and data stores
   - Integration points
   - Infrastructure components
   - Third-party dependencies

2. **Technology Stack Analysis**:
   - Languages and frameworks with versions
   - Database technologies
   - Middleware and messaging
   - Security infrastructure
   - Monitoring and logging

3. **Data Landscape**:
   - Data stores and sizes
   - Data relationships
   - Data quality assessment
   - Sensitive data identification
   - Archive and retention status

4. **Integration Analysis**:
   - Upstream systems
   - Downstream systems
   - API inventory
   - File transfer interfaces
   - Real-time vs batch

5. **Pain Points and Issues**:
   - Technical debt inventory
   - Performance issues
   - Scalability limitations
   - Security gaps
   - Maintenance challenges
   - Compliance gaps

6. **Business Process Analysis**:
   - Critical business processes
   - Process dependencies
   - SLA requirements
   - Seasonal patterns

Return as comprehensive JSON with detailed current state."""
        },
        {
            'section': 'target_state_design',
            'prompt': f"""You are a Migration Architect designing the target state.

{base_context}

Generate EXTREMELY DETAILED TARGET STATE DESIGN (target: 8-10 pages):

1. **Target Architecture**:
   - Architecture patterns (microservices, serverless, etc.)
   - Component design
   - Data architecture
   - Integration architecture
   - Security architecture

2. **Technology Decisions** (with detailed rationale):
   - Cloud platform selection
   - Compute services
   - Data services
   - Integration services
   - Security services
   - DevOps tooling

3. **Data Strategy**:
   - Data migration approach
   - Schema transformations
   - Data cleansing requirements
   - Archive strategy

4. **Integration Strategy**:
   - API design standards
   - Event-driven patterns
   - Legacy integration approach

5. **Security Strategy**:
   - Identity and access management
   - Network security
   - Data protection
   - Compliance approach

6. **Operational Model**:
   - Monitoring and alerting
   - Incident management
   - Change management
   - Capacity management

7. **Cost Model**:
   - Infrastructure costs
   - Licensing costs
   - Operational costs
   - Comparison with current state

Return as comprehensive JSON with target state design."""
        },
        {
            'section': 'migration_phases',
            'prompt': f"""You are a Migration Architect planning migration phases.

{base_context}

Generate EXTREMELY DETAILED MIGRATION PHASES (target: 10-12 pages):

Create 6 detailed phases, each including:

1. **Phase Name and Objectives**:
   - Clear phase title
   - 5-8 specific objectives
   - Success criteria

2. **Duration and Timeline**:
   - Estimated duration
   - Key milestones
   - Dependencies on other phases

3. **Detailed Activities** (15-20 per phase):
   - Activity description
   - Responsible team
   - Duration estimate
   - Deliverables
   - Dependencies

4. **Resources Required**:
   - Team composition
   - Skill requirements
   - Infrastructure needs
   - Tool requirements

5. **Deliverables**:
   - Documentation
   - Code/configuration
   - Test evidence
   - Sign-off requirements

6. **Phase-Specific Risks**:
   - Risk identification
   - Probability and impact
   - Mitigation strategies
   - Contingency plans

7. **Exit Criteria**:
   - Specific measurable criteria
   - Required approvals
   - Quality gates

Phases should include:
- Phase 1: Discovery and Planning
- Phase 2: Environment Setup
- Phase 3: Data Migration
- Phase 4: Application Migration
- Phase 5: Testing and Validation
- Phase 6: Cutover and Hypercare

Return as comprehensive JSON with all 6 phases."""
        },
        {
            'section': 'risk_and_rollback',
            'prompt': f"""You are a Migration Architect planning risk mitigation and rollback.

{base_context}

Generate EXTREMELY DETAILED RISK AND ROLLBACK PLAN (target: 6-8 pages):

1. **Risk Assessment** (20+ risks):
   Each risk should include:
   - Risk ID
   - Risk description
   - Category (Technical/Business/Operational/Security)
   - Probability (High/Medium/Low)
   - Impact (High/Medium/Low)
   - Risk score
   - Trigger indicators
   - Mitigation strategy
   - Contingency plan
   - Owner

2. **Rollback Strategy**:
   For each phase, define:
   - Rollback triggers
   - Rollback decision matrix
   - Rollback procedure (step-by-step)
   - Data recovery approach
   - Communication plan
   - Time estimates
   - Validation steps

3. **Go/No-Go Criteria**:
   - Technical readiness criteria
   - Business readiness criteria
   - Operational readiness criteria
   - Decision authority matrix

4. **Communication Plan**:
   - Stakeholder communication matrix
   - Escalation procedures
   - Status reporting cadence
   - Issue notification process

5. **Contingency Plans**:
   - Major failure scenarios
   - Response procedures
   - Recovery time objectives

Return as comprehensive JSON with full risk and rollback details."""
        }
    ]


# ==================== REVERSE ENGINEERING PROMPTS ====================

def _get_reverse_eng_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'system_overview',
            'prompt': f"""You are a Reverse Engineering Specialist documenting an existing system.

{base_context}

Generate SYSTEM OVERVIEW:
1. **Purpose**: What does this system do?
2. **History**: Inferred history and evolution
3. **Stakeholders**: Who uses and maintains it
4. **Business Context**: Business processes supported

Return as detailed JSON."""
        },
        {
            'section': 'architecture_analysis',
            'prompt': f"""You are a Reverse Engineering Specialist analyzing architecture.

{base_context}

Generate ARCHITECTURE ANALYSIS:
1. **Architecture Style**: Patterns used (MVC, Microservices, etc.)
2. **Component Inventory**: All major components with responsibilities
3. **Component Interactions**: How components communicate
4. **Data Flow**: How data moves through system
5. **Deployment Architecture**: How it's deployed

Return as detailed JSON with diagrams described in text."""
        },
        {
            'section': 'technology_stack',
            'prompt': f"""You are a Reverse Engineering Specialist documenting technology.

{base_context}

Generate TECHNOLOGY STACK ANALYSIS:
1. **Languages**: Programming languages with versions
2. **Frameworks**: All frameworks identified
3. **Libraries**: Third-party dependencies
4. **Databases**: Data stores used
5. **Infrastructure**: Servers, cloud services
6. **DevOps Tools**: Build, deploy, monitor tools

Return as detailed JSON with version info where identifiable."""
        },
        {
            'section': 'data_model',
            'prompt': f"""You are a Reverse Engineering Specialist analyzing data.

{base_context}

Generate DATA MODEL ANALYSIS:
1. **Entities**: All data entities discovered
2. **Relationships**: How entities relate
3. **Data Stores**: Where data is persisted
4. **Data Quality**: Issues found with data

Return as detailed JSON."""
        },
        {
            'section': 'technical_debt',
            'prompt': f"""You are a Reverse Engineering Specialist identifying technical debt.

{base_context}

Generate TECHNICAL DEBT ASSESSMENT:
1. **Code Quality Issues**: Identified problems
2. **Architecture Issues**: Structural problems
3. **Security Gaps**: Potential security issues
4. **Performance Issues**: Bottlenecks identified
5. **Maintainability Issues**: Hard to maintain areas
6. **Recommendations**: Prioritized improvements

Return as detailed JSON with severity ratings."""
        }
    ]


# ==================== TDD PROMPTS ====================

def _get_tdd_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'technical_overview',
            'prompt': f"""You are a Technical Architect creating a Technical Design Document.

{base_context}

IMPORTANT: All technical design decisions must support the CONFIRMED USER STORIES above. Reference specific story IDs when explaining design choices.

Generate TECHNICAL OVERVIEW:
1. **System Purpose**: Technical purpose and goals
2. **Design Principles**: Guiding technical principles
3. **Quality Attributes**: Key non-functional priorities
4. **Constraints**: Technical constraints
5. **Assumptions**: Technical assumptions

Return as detailed JSON."""
        },
        {
            'section': 'architecture_design',
            'prompt': f"""You are a Technical Architect designing architecture.

{base_context}

Generate ARCHITECTURE DESIGN:
1. **Architecture Style**: Pattern chosen with rationale
2. **Component Design**: Each component with:
   - Name and purpose
   - Responsibilities
   - Interfaces
   - Dependencies
3. **Interaction Patterns**: How components communicate
4. **Technology Selection**: Technologies with rationale

Return as detailed JSON."""
        },
        {
            'section': 'data_design',
            'prompt': f"""You are a Technical Architect designing data layer.

{base_context}

Generate DATA DESIGN:
1. **Database Selection**: Type with rationale
2. **Schema Design**: Tables/collections with:
   - Fields and types
   - Indexes
   - Constraints
3. **Data Access Patterns**: How data is accessed
4. **Caching Strategy**: What and how to cache
5. **Data Migration**: How existing data moves

Return as detailed JSON."""
        },
        {
            'section': 'api_design',
            'prompt': f"""You are a Technical Architect designing APIs.

{base_context}

Generate API DESIGN:
1. **API Style**: REST/GraphQL/gRPC with rationale
2. **Endpoints**: All endpoints with:
   - Path
   - Method
   - Request/Response schemas
   - Authentication
   - Rate limits
3. **Error Handling**: Standard error responses
4. **Versioning**: API versioning strategy

Return as detailed JSON."""
        },
        {
            'section': 'security_design',
            'prompt': f"""You are a Technical Architect designing security.

{base_context}

Generate SECURITY DESIGN:
1. **Authentication Design**: How users authenticate
2. **Authorization Design**: How permissions work
3. **Data Security**: Encryption, masking
4. **Network Security**: Firewalls, WAF
5. **Security Monitoring**: Logging, alerting

Return as detailed JSON."""
        },
        {
            'section': 'deployment_design',
            'prompt': f"""You are a Technical Architect designing deployment.

{base_context}

Generate DEPLOYMENT DESIGN:
1. **Infrastructure**: Cloud/on-premise specs
2. **Containerization**: Docker/Kubernetes design
3. **CI/CD Pipeline**: Build and deploy process
4. **Environment Strategy**: Dev/Test/Prod setup
5. **Scaling Strategy**: How to scale
6. **Monitoring**: Observability setup

Return as detailed JSON."""
        }
    ]


# ==================== DB ANALYSIS PROMPTS ====================

def _get_db_analysis_prompts(base_context: str) -> List[Dict]:
    return [
        {
            'section': 'database_overview',
            'prompt': f"""You are a Database Architect analyzing database design.

{base_context}

Generate DATABASE OVERVIEW:
1. **Database Type**: SQL/NoSQL and specific product
2. **Schema Overview**: High-level structure
3. **Size Estimates**: Data volumes
4. **Access Patterns**: How database is used

Return as detailed JSON."""
        },
        {
            'section': 'schema_analysis',
            'prompt': f"""You are a Database Architect analyzing schema.

{base_context}

Generate SCHEMA ANALYSIS:
1. **Tables/Collections**: Each with:
   - Name and purpose
   - Columns with types
   - Primary keys
   - Foreign keys
   - Constraints
2. **Relationships**: All relationships with cardinality
3. **Normalization Level**: Assessment of normalization

Return as detailed JSON."""
        },
        {
            'section': 'index_analysis',
            'prompt': f"""You are a Database Architect analyzing indexes.

{base_context}

Generate INDEX ANALYSIS:
1. **Existing Indexes**: Indexes found/inferred
2. **Missing Indexes**: Recommended indexes
3. **Index Strategy**: Overall indexing approach
4. **Query Patterns**: Queries that need optimization

Return as detailed JSON."""
        },
        {
            'section': 'optimization_recommendations',
            'prompt': f"""You are a Database Architect providing recommendations.

{base_context}

Generate OPTIMIZATION RECOMMENDATIONS:
1. **Schema Improvements**: Structural changes
2. **Query Optimizations**: Query improvements
3. **Index Recommendations**: Index changes
4. **Partitioning Strategy**: If applicable
5. **Archival Strategy**: Data retention
6. **Performance Tuning**: Database settings

Return as detailed JSON with priority and impact for each."""
        }
    ]
