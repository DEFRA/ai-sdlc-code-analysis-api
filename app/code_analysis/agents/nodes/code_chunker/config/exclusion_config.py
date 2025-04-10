"""Exclusion configuration for code analysis.

This module defines the default patterns for files and directories that should be
excluded from code analysis.
"""

# Default file patterns to exclude from analysis
DEFAULT_EXCLUDE_FILES = [
    # JavaScript/Node.js
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    # Python
    "poetry.lock",
    "Pipfile.lock",
    "requirements.txt.sha256",
    # Java
    "gradle-wrapper.jar",
    "maven-wrapper.jar",
    # C#/.NET
    "packages.lock.json",
    "project.assets.json",
    "project.nuget.cache",
    # Swift/iOS
    "Podfile.lock",
    # Ruby
    "Gemfile.lock",
    # Build outputs (any language)
    "yarn-error.log",
    "npm-debug.log",
]

# Default directory patterns to exclude from analysis
# Note: All directory patterns MUST end with a trailing slash
DEFAULT_EXCLUDE_DIRS = [
    # Common directories to ignore
    ".git/",
    "__pycache__/",
    "node_modules/",
    "venv/",
    ".venv/",
    "dist/",
    "build/",
    ".idea/",
    ".vscode/",
]

# Default wildcard patterns to exclude from analysis
DEFAULT_EXCLUDE_WILDCARDS = [
    "*.pyc",  # Compiled Python files
    "*.pyo",  # Optimized Python files
    "*.pyd",  # Python extension modules
    "*.so",  # Shared object files
    "*.dll",  # Dynamic link libraries
    "*.exe",  # Executables
    "*.out",  # Output files
    "*.bin",  # Binary files
    "*.o",  # Object files
    "*.a",  # Static libraries
    "*.class",  # Java class files
]

# Combined default exclude patterns (all types)
DEFAULT_EXCLUDE_PATTERNS = (
    DEFAULT_EXCLUDE_FILES + DEFAULT_EXCLUDE_DIRS + DEFAULT_EXCLUDE_WILDCARDS
)
