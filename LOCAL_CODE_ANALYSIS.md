# Local Code Analysis Endpoint

This document describes the new local code analysis functionality that processes code already available in the `/repository-ingest` folder.

## Overview

The local code analysis endpoint allows you to analyze code that's already been copied locally into the `repository-ingest` folder, bypassing the need to provide a GitHub repository URL.

## Usage

### 1. Prepare Your Code

Copy the code you want to analyze into the `repository-ingest` folder at the root of the project:

```bash
# Copy your code into the repository-ingest folder
cp -r /path/to/your/code/* repository-ingest/
```

### 2. Trigger Analysis

Make a POST request to the new local endpoint:

```bash
curl -X POST "http://localhost:8085/api/v1/code-analysis/local" \
     -H "Content-Type: application/json" \
     -d '{"description": "My local code analysis"}'
```

The endpoint accepts an optional `description` field. If not provided, it defaults to "Local repository analysis".

### 3. Check Status

Use the returned `thread_id` to check the analysis status using the existing endpoints:

```bash
# Check analysis status
curl "http://localhost:8085/api/v1/code-analysis/{thread_id}"

# Get consolidated report
curl "http://localhost:8085/api/v1/code-analysis/{thread_id}/consolidated-report"

# Get product requirements
curl "http://localhost:8085/api/v1/code-analysis/{thread_id}/product-requirements-report"
```

## API Specification

### POST `/api/v1/code-analysis/local`

Triggers a new code analysis for the local `repository-ingest` folder.

**Request Body:**
```json
{
  "description": "Optional description for the analysis"
}
```

**Response:**
- **Status:** 202 Accepted
- **Body:**
```json
{
  "thread_id": "unique-thread-identifier"
}
```

**Error Responses:**
- **404 Not Found:** The `repository-ingest` folder doesn't exist
- **500 Internal Server Error:** Analysis failed to start

## Implementation Details

### Architecture

The local code analysis uses the same LangGraph workflow as the GitHub repository analysis:

1. **Local Path Processing:** Uses the existing `RepositoryManager` class which already supports local paths
2. **Code Chunking:** Same chunking logic applies to local code
3. **Analysis Pipeline:** Identical analysis nodes and workflow
4. **Report Generation:** Same report generation process

### Code Structure

- **Model:** `LocalCodeAnalysisRequest` in `app/code_analysis/models/code_analysis.py`
- **Service:** `trigger_local_code_analysis()` in `app/code_analysis/services/code_analysis.py`
- **API:** `create_local_code_analysis()` in `app/code_analysis/api/v1/code_analysis.py`

### Differences from GitHub Analysis

1. **No Cloning:** Local analysis skips the git clone step
2. **Direct Path Access:** Uses absolute path to `repository-ingest` folder
3. **Path Validation:** Validates that the folder exists before starting analysis
4. **Same Processing:** All other processing steps are identical

## Example Workflow

```python
# Example using Python requests
import requests

# 1. Trigger local analysis
response = requests.post(
    "http://localhost:8085/api/v1/code-analysis/local",
    json={"description": "Analyzing my project"}
)
thread_id = response.json()["thread_id"]

# 2. Poll for completion (analysis runs asynchronously)
import time
while True:
    status_response = requests.get(f"http://localhost:8085/api/v1/code-analysis/{thread_id}")
    if status_response.status_code == 200:
        analysis = status_response.json()
        if analysis.get("consolidated_report"):
            print("Analysis complete!")
            break
    time.sleep(10)  # Wait 10 seconds before checking again

# 3. Get the final report
report_response = requests.get(f"http://localhost:8085/api/v1/code-analysis/{thread_id}/consolidated-report")
print(report_response.text)
```

## Benefits

1. **No GitHub Dependency:** Analyze code without needing a GitHub repository
2. **Privacy:** Keep sensitive code local without pushing to remote repositories
3. **Flexibility:** Analyze any code structure, including partial codebases
4. **Same Quality:** Uses identical analysis pipeline as GitHub-based analysis
