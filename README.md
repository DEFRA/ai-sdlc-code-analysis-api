# ai-sdlc-code-analysis-api

A FastAPI service for analysing code repositories as part of the AI SDLC project. This service provides code analysis capabilities through an API and leverages LangGraph for AI-powered code analysis workflows.

- [ai-sdlc-code-analysis-api](#ai-sdlc-code-analysis-api)
  - [Requirements](#requirements)
    - [Python](#python)
    - [Linting and Formatting](#linting-and-formatting)
    - [Docker](#docker)
  - [Local development](#local-development)
    - [Setup & Configuration](#setup--configuration)
    - [Development](#development)
    - [Testing](#testing)
    - [Production Mode](#production-mode)
  - [API endpoints](#api-endpoints)
  - [Architecture](#architecture)
    - [Data Model](#data-model)
    - [System Components](#system-components)
    - [Code Analysis Workflow](#code-analysis-workflow)
  - [Custom Cloudwatch Metrics](#custom-cloudwatch-metrics)
  - [Pipelines](#pipelines)
    - [Dependabot](#dependabot)
    - [SonarCloud](#sonarcloud)
  - [Licence](#licence)
    - [About the licence](#about-the-licence)
  - [Graph Visualizations](#graph-visualizations)
    - [create_code_analysis_graph](#create_code_analysis_graph)

## Requirements

### Python

Please install python `>= 3.12` and [configure your python virtual environment](https://fastapi.tiangolo.com/virtual-environments/#create-a-virtual-environment):

```python
# create the virtual environment
python -m venv .venv

# activate the the virtual environment in the command line
source .venv/bin/activate

# update pip
python -m pip install --upgrade pip

# install the dependencies
pip install -r requirements-dev.txt

# install the pre-commit hooks
pre-commit install
```

This opinionated template uses the [`Fast API`](https://fastapi.tiangolo.com/) Python API framework along with [LangGraph](https://python.langchain.com/docs/langgraph) for orchestrating AI-powered workflows.

This and all other runtime python libraries must reside in `requirements.txt`

Other non-runtime dependencies used for dev & test must reside in `requirements-dev.txt`

### Linting and Formatting

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting Python code.

#### Running Ruff

To run Ruff from the command line:

```bash
# Run linting with auto-fix
ruff check . --fix

# Run formatting
ruff format .
```

#### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run linting and formatting checks automatically before each commit.

The pre-commit configuration is defined in `.pre-commit-config.yaml`

To set up pre-commit hooks:

```bash
# Set up the git hooks
pre-commit install
```

To run the hooks manually on all files:

```bash
pre-commit run --all-files
```

#### VS Code Configuration

For the best development experience, configure VS Code to use Ruff:

1. Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for VS Code
2. Configure your VS Code settings (`.vscode/settings.json`):

```json
{
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit"
    },
    "ruff.lint.run": "onSave",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    }
}
```

This configuration will:

- Format your code with Ruff when you save a file
- Fix linting issues automatically when possible
- Organise imports according to isort rules

#### Ruff Configuration

Ruff is configured in the `.ruff.toml` file

### Docker

This repository uses Docker throughout its lifecycle i.e. both for local development and the environments. A benefit of this is that environment variables & secrets are managed consistently throughout the lifecycle

See the `Dockerfile` and `compose.yml` for details

## Local development

### Setup & Configuration

Follow the convention below for local environment variables and secrets in local development. Note that it does not use .env or python-dotenv as this is not the convention in the CDP environment.

**Environment variables:** `compose/aws.env`.

**Secrets:** `compose/secrets.env`. You need to create this, as it's excluded from version control.

**Libraries:** Ensure the python virtual environment is configured and libraries are installed using `requirements-dev.txt`, [as above](#python)

**Pre-Commit Hooks:** Ensure you install the pre-commit hooks, as above

### Development

The app can be run locally using Docker compose. This template contains a local environment with:

- Localstack
- MongoDB
- This service

To run the application in development mode:

```bash
docker compose watch
```

The service will then run on `http://localhost:8085`

### Testing

Ensure the python virtual environment is configured and libraries are installed using `requirements-dev.txt`, [as above](#python)

Testing follows the [FastApi documented approach](https://fastapi.tiangolo.com/tutorial/testing/); using pytest & starlette.

To test the application run:

```bash
pytest
```

### Production Mode

To mimic the application running in production mode locally run:

```bash
docker compose up --build -d
```

The service will then run on `http://localhost:8085`

Stop the application with

```bash
docker compose down
```

## API endpoints

| Endpoint                         | Method | Description                                                    |
| :------------------------------- | :----- | :------------------------------------------------------------- |
| `/docs`                          | GET    | Automatic API Swagger documentation                            |
| `/api/v1/code-analysis`          | POST   | Triggers a new code analysis for a repository URL              |
| `/api/v1/code-analysis/{thread_id}` | GET  | Gets the current state of a code analysis by thread ID        |

## Architecture

The Code Analysis API is built using FastAPI and integrates with LangGraph for running AI-powered code analysis workflows. The system architecture is detailed below.

### Data Model

```mermaid
classDiagram
    class CodeAnalysisState {
        +String repo_url
    }
    class CodeAnalysisRequest {
        +HttpUrl repo_url
    }
    class CodeAnalysisResponse {
        +String thread_id
    }

    CodeAnalysisRequest --> CodeAnalysisResponse: triggers
    CodeAnalysisResponse --> CodeAnalysisState: references
```

### System Components

```mermaid
flowchart TB
    Client[Client] --> API[FastAPI Service]
    API --> Router[Code Analysis Router]
    Router --> Service[Code Analysis Service]
    Service --> Agent[LangGraph Agent]
    Agent --> MongoDB[(MongoDB)]
```

### Code Analysis Workflow

The code analysis workflow is implemented using LangGraph, which provides a framework for creating stateful, multi-step reasoning systems with AI models. The workflow follows these steps:

1. Client submits a repository URL through the API
2. The system generates a unique thread ID for the analysis
3. An asynchronous LangGraph agent is created to perform the analysis
4. Analysis state is persisted in MongoDB using LangGraph checkpoints
5. Clients can query the status of the analysis using the thread ID

The LangGraph agent is defined in the `app/code_analysis/agents/code_analysis.py` file and uses a state graph to manage the analysis workflow. The current implementation includes an initialization step that sets up the analysis state.

## Custom Cloudwatch Metrics

Uses the [aws embedded metrics library](https://github.com/awslabs/aws-embedded-metrics-python). An example can be found in `metrics.py`

In order to make this library work in the environments, the environment variable `AWS_EMF_ENVIRONMENT=local` is set in the app config. This tells the library to use the local cloudwatch agent that has been configured in CDP, and uses the environment variables set up in CDP `AWS_EMF_AGENT_ENDPOINT`, `AWS_EMF_LOG_GROUP_NAME`, `AWS_EMF_LOG_STREAM_NAME`, `AWS_EMF_NAMESPACE`, `AWS_EMF_SERVICE_NAME`

## Pipelines

### Dependabot

We have added an example dependabot configuration file to the repository. You can enable it by renaming
the [.github/example.dependabot.yml](.github/example.dependabot.yml) to `.github/dependabot.yml`

### SonarCloud

Instructions for setting up SonarCloud can be found in [sonar-project.properties](./sonar-project.properties)

## Licence

THIS INFORMATION IS LICENSED UNDER THE CONDITIONS OF THE OPEN GOVERNMENT LICENCE found at:

<http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3>

The following attribution statement MUST be cited in your products and applications when using this information.

> Contains public sector information licensed under the Open Government licence v3

### About the licence

The Open Government Licence (OGL) was developed by the Controller of Her Majesty's Stationery Office (HMSO) to enable
information providers in the public sector to license the use and re-use of their information under a common open
licence.

It is designed to encourage use and re-use of information freely and flexibly, with only a few conditions.

## Graph Visualizations

This section contains automatically generated visualizations of the LangGraph workflows in this project.


### create_code_analysis_graph

# Graph: create_code_analysis_graph

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	code_chunker(code_chunker)
	process_code_chunks(process_code_chunks)
	generate_data_model_report(generate_data_model_report)
	generate_interfaces_report(generate_interfaces_report)
	generate_business_logic_report(generate_business_logic_report)
	generate_dependencies_report(generate_dependencies_report)
	generate_configuration_report(generate_configuration_report)
	generate_infrastructure_report(generate_infrastructure_report)
	generate_non_functional_report(generate_non_functional_report)
	generate_consolidated_report(generate_consolidated_report)
	generate_product_requirements(generate_product_requirements)
	__end__([<p>__end__</p>]):::last
	__start__ --> code_chunker;
	code_chunker --> process_code_chunks;
	generate_business_logic_report --> generate_dependencies_report;
	generate_configuration_report --> generate_infrastructure_report;
	generate_consolidated_report --> generate_product_requirements;
	generate_data_model_report --> generate_interfaces_report;
	generate_dependencies_report --> generate_configuration_report;
	generate_infrastructure_report --> generate_non_functional_report;
	generate_interfaces_report --> generate_business_logic_report;
	generate_non_functional_report --> generate_consolidated_report;
	generate_product_requirements --> __end__;
	process_code_chunks --> generate_data_model_report;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```



## Project Structure
