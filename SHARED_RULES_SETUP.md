# Shared AI Assistant Rules Setup

This document explains how we've set up shared rule files that work with both Cursor and GitHub Copilot.

## Overview

We've created a system where AI coding assistants (Cursor and GitHub Copilot) can reference the same set of rules, ensuring consistent AI assistance across different tools and developers.

The implementation involves:
1. A central `rules/` directory containing markdown files with rules
2. Symlinks from this directory to Cursor's rules folder
3. A VSCode settings configuration for GitHub Copilot

## Implementation Details

### Directory Structure

```
project-root/
├── rules/                    # Central location for all rule files
│   ├── python-code-style.md
│   ├── langgraph-*.md
│   └── ...
├── .cursor/                  # Cursor configuration directory
│   └── rules/                # Contains symlinks to ../rules/*
└── .vscode/                  # VSCode configuration directory
    └── settings.json         # Contains Copilot rules configuration
```

### Setup Steps

#### 1. Create the Central Rules Directory

First, we created a central `rules/` directory in the project root to store all our rule files:

```bash
mkdir -p rules
```

#### 2. Create Rule Files

We created markdown files in the `rules/` directory with clear, descriptive names:

```bash
# Example of creating rule files
touch rules/python-code-style.md
touch rules/langgraph-tool-use.md
# ... additional rule files
```

#### 3. Configure Cursor

For Cursor to use these rules:

1. Create the Cursor rules directory (if it doesn't exist):
   ```bash
   mkdir -p .cursor/rules
   ```

2. Create symlinks from the central rules to Cursor's rules folder:
   ```bash
   # From project root
   ln -s ../rules/* .cursor/rules/
   ```

#### 4. Configure GitHub Copilot

For GitHub Copilot to use these rules, we created/updated `.vscode/settings.json`:

```json
{
  "github.copilot.advanced": {
    "rules": {
      "*": [
        { "path": "rules/python-code-style.md" }
      ],
      "**/*.py": [
        { "path": "rules/python-project.md" },
        { "path": "rules/langgraph-tool-use.md" },
        { "path": "rules/langgraph-type-safety.md" }
        // ... additional language-specific rules
      ]
    }
  }
}
```

### Rule Format

Each rule file is written in markdown and follows a consistent format:

```markdown
# Rule Title

Description of what this rule is about and why it's important.

## Guidelines

1. First guideline
2. Second guideline
3. ...

## Examples

### Good Example
```python
# Good code example
```

### Bad Example
```python
# Bad code example
```
```

## Maintenance

When updating rules:

1. Always edit the files in the central `rules/` directory
2. The changes will automatically be reflected in Cursor through the symlinks
3. GitHub Copilot will pick up the changes through the file paths defined in settings.json

## Benefits

- **Single Source of Truth**: Rules are defined once in a single location
- **Consistency**: All developers get the same AI assistance regardless of which tool they use
- **Version Control**: Rules are tracked in version control along with the codebase
- **Easy Updates**: Changes to rules only need to be made in one place

## Implementation History

The setup was completed in three commits:

1. Initial setup of shared rules structure with hooks into both tools
2. Configuration to apply specific rules to matching file globs
3. Standardization of all rule files to use the markdown (.md) extension
