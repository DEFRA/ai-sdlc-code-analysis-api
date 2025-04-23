# LangGraph Node Testing Scripts

This directory contains scripts for testing individual [LangGraph](https://langchain-ai.github.io/langgraph/) nodes in isolation from the full graph execution flow.

## Purpose

LangGraph agents in this project are composed of multiple nodes working together. While integration tests verify the end-to-end functionality, these scripts allow developers to:

1. Run individual LangGraph nodes in isolation
2. Debug node behavior with specific input states
3. Experiment with model prompts and configurations
4. Generate sample outputs for documentation or testing

## Directory Structure

```
run_langgraph_nodes/
├── data/                  # Data files for testing nodes
│   ├── setup/             # Input test data for nodes
│   └── results/           # Output results from node execution
├── utils.py               # Shared utility functions
├── analyse_code_chunk.py  # Tests the code chunk analysis node
└── generate_data_model_report.py  # Tests the data model report generation node
```

## Available Scripts

### analyse_code_chunk.py

Tests the `analyse_code_chunk` node that analyzes a code chunk and extracts key information including data models, interfaces, business logic, and more.

**Usage:**
```bash
python scripts/run_langgraph_nodes/analyse_code_chunk.py
```

**Input:** Expects a JSON file at `data/setup/code_chunk.json` containing a serialized code chunk.

**Output:**
- Prints analysis results to the console
- Saves full results to `data/results/analyze_code_chunk_result.json`

### generate_data_model_report.py

Tests the `generate_data_model_report` node that creates a comprehensive data model report from analyzed code chunks.

**Usage:**
```bash
python scripts/run_langgraph_nodes/generate_data_model_report.py
```

**Input:** Expects a JSON file at `data/setup/analyzed_code_chunks.json` containing analyzed code chunks.

**Output:**
- Prints the generated data model report to the console
- Saves full results to `data/results/data_model_report_result.json`

## Utilities

The `utils.py` module provides shared functionality for all node testing scripts, including:

- Environment variable management
- Test data loading
- Result saving
- Path resolution
- Error handling

## Adding New Scripts

When adding new node testing scripts:

1. Create a new Python file in this directory
2. Import common utilities from `utils.py`
3. Place test input data in `data/setup/`
4. Save results to `data/results/`
5. Follow the established pattern for environment setup and error handling

## Environment Setup

These scripts require environment variables typically sourced from:
- `compose/secrets.env`
- `compose/aws.env`

Make sure these files exist and contain the required variables before running the scripts
