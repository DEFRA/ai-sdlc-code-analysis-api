# Python Project Guidelines

## Project Stack & Architecture
- Primary Framework: Python with FastAPI
- AI Components: LangGraph, LangChain
- Development Approach: Async by default, Security-first

## Directory Structure
```
src/
├── api/v1/      # Routing and HTTP endpoints
├── services/    # Business logic
├── repositories/# Data access
├── agents/      # LangGraph AI agents
├── utils/       # Utility functions
├── config/      # Configuration
├── database/    # Database operations
└── models/      # Data models
```

## Code Style Standards

### Base Standards & Tools
- Follow PEP 8 conventions
- Use Ruff for linting and formatting
- Use Pyright for type checking

### Formatting Rules
- Indentation: 4 spaces
- Maximum line length: 88 characters
- String quotes: Double quotes preferred
- Docstring style: Google format

### Naming Conventions
- Functions/Variables/Modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

### Import Structure
1. Standard library imports
2. Third-party imports (fastapi, pydantic, motor, pytest)
3. Local application imports

### Function Guidelines
- Maximum length: 50 lines
- Maximum nesting: 3 levels
- Follow single responsibility principle
- Include clear return type annotations

### Development Principles
- Security-first approach
- Clean code practices
- Validate all inputs
- No secrets in code
- Encrypt sensitive data

### Git Commit Standards
- Use conventional commit prefixes (feat:, fix:, etc.)
- Include concise messages
- Reference related issues
- No sensitive information in commits

### IDE Configuration
- Format on save with Ruff
- Auto-fix linting issues when possible
- Use VS Code with Ruff extension
