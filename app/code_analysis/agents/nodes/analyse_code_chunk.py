import json
import os
from logging import getLogger

import tiktoken
from langchain_aws import ChatBedrock

from app.code_analysis.agents.states.code_chuck_analysis import CodeChunkAnalysisState
from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk

logger = getLogger(__name__)


def analyse_code_chunk(state: CodeChunkAnalysisState) -> CodeChunkAnalysisState:
    """Analyses a given code chunk"""

    logger.info("Analyzing code chunk %s", state.code_chunk.chunk_id)

    # Initialize the Claude model using Bedrock
    model = ChatBedrock(
        model_id=os.environ.get("AWS_BEDROCK_MODEL"),
        region_name=os.environ.get("AWS_REGION"),
        model_kwargs={"temperature": 0, "max_tokens": 8192},
    )

    # Prepare the input for the model
    code_chunk_data = {
        "chunk_id": state.code_chunk.chunk_id,
        "description": state.code_chunk.description,
        "files": state.code_chunk.files,
        "content": state.code_chunk.content,
    }

    # Format the user prompt with the code chunk data
    user_prompt = f"""Analyze the following code chunk, in the following json format.

{json.dumps(code_chunk_data, indent=2)}

Your analysis must return ONLY a valid JSON object with these fields:

1. summary (required): Concise functional description of what this code does from a business perspective (3-5 sentences).

2. data_model (string): If applicable, include:
   - Logical data models and entities
   - Mermaid ERD diagram as a string (wrapped in triple backticks with "mermaid" tag)
   - Detailed breakdown of each model's fields, types, and relationships
   - Data flow and transformations
   - Data validation and integrity checks
   - Set to null if no data models are present

3. interfaces (string): If applicable, include:
   - User interfaces (UI)
   - API endpoints with request/response formats
   - Batch processing interfaces
   - Event-driven interfaces (e.g., message queues)
   - Any other interfaces exposed by the code
   - Set to null if no interfaces are defined

4. business_logic (string): If applicable, include:
   - Core business rules and domain logic
   - Business process flows
   - Business rules
   - Separation of concerns between business logic and other layers
   - Domain-driven design patterns
   - Set to null if no significant business logic exists

5. dependencies (string): If applicable, include:
   - External dependencies (libraries, frameworks)
   - API calls or external services
   - Database connections and ORM usage
   - Third-party integrations
   - Versioning and compatibility considerations
   - Set to null if no dependencies exist

6. configuration (string): If applicable, include:
   - Configuration files (e.g., YAML, JSON)
   - Configuration variables with defaults and valid options
   - Environment variables and config files
   - Secrets management and sensitive data handling
   - Set to null if no configuration exists

7. infrastructure (string): If applicable, include:
   - Infrastructure as code (IaC) elements (e.g., Terraform, CloudFormation)
   - Deployment requirements and environment needs
   - Resource requirements and scaling considerations
   - Set to null if no infrastructure elements exist

8. non_functional (string): If applicable, include:
   - Performance, security, and reliability aspects
   - Error handling, logging, monitoring, and alerting
   - Compliance considerations
   - Data and privacy considerations
   - Set to null if no non-functional elements exist

Include the chunk_id in your response JSON object. Your response must be a valid JSON object following EXACTLY this structure:

{{
  "chunk_id": "{state.code_chunk.chunk_id}",
  "summary": "string",
  "data_model": "string",
  "interfaces": "string",
  "business_logic": "string",
  "dependencies": "string",
  "configuration": "string",
  "infrastructure": "string",
  "non_functional": "string"
}}

All string fields should contain detailed markdown-formatted text. For fields with no applicable content, use null instead of an empty string. Do NOT include any content outside this JSON structure."""

    # System prompt
    system_prompt = """You are a specialized code analysis system that produces ONLY valid JSON output following the CodeAnalysisChunk schema. Your entire response must be parseable JSON with no surrounding text, markdown, explanations, or formatting. Never include anything outside the JSON structure. Always include all fields from the schema, using null for fields where no applicable content exists in the code chunk. Maintain this strict JSON-only format under all circumstances."""

    # Call the model with the prompts
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Count input tokens before making API call
    token_counter = tiktoken.get_encoding("cl100k_base")
    system_tokens = len(token_counter.encode(system_prompt))
    user_tokens = len(token_counter.encode(user_prompt))
    total_input_tokens = system_tokens + user_tokens
    logger.info(
        "Chunk %s - Input token count - System: %d, User: %d, Total: %d",
        state.code_chunk.chunk_id,
        system_tokens,
        user_tokens,
        total_input_tokens,
    )

    # Check if input tokens exceed 200,000 and log files array if they do
    if total_input_tokens > 150000:
        logger.warning(
            "Chunk %s - Input token count exceeds 150,000 tokens (%d). Files in this chunk: %s",
            state.code_chunk.chunk_id,
            total_input_tokens,
            json.dumps(state.code_chunk.files, indent=2),
        )
        logger.warning(
            "Chunk %s - Content causing token limit excess: %s",
            state.code_chunk.chunk_id,
            state.code_chunk.content,
        )

    # Use the structured model to get a properly parsed response
    structured_model = model.with_structured_output(CodeAnalysisChunk)
    analyzed_code_chunk = structured_model.invoke(messages)

    # If for some reason the chunk_id was not set, set it manually
    if analyzed_code_chunk.chunk_id != state.code_chunk.chunk_id:
        logger.warning(
            "Chunk ID in response (%s) doesn't match expected ID (%s). Fixing...",
            analyzed_code_chunk.chunk_id,
            state.code_chunk.chunk_id,
        )
        # Create a new instance with the correct chunk_id
        analyzed_code_chunk_dict = analyzed_code_chunk.model_dump()
        analyzed_code_chunk_dict["chunk_id"] = state.code_chunk.chunk_id
        analyzed_code_chunk = CodeAnalysisChunk(**analyzed_code_chunk_dict)

    # Count output tokens (approximate based on JSON serialization)
    output_json = json.dumps(analyzed_code_chunk.model_dump())
    output_tokens = len(token_counter.encode(output_json))
    logger.info(
        "Chunk %s - Output token count: %d", state.code_chunk.chunk_id, output_tokens
    )
    logger.info(
        "Chunk %s - Total token usage (input + output): %d",
        state.code_chunk.chunk_id,
        total_input_tokens + output_tokens,
    )

    logger.info("Successfully analyzed code chunk %s", state.code_chunk.chunk_id)

    return {
        "analyzed_code_chunk": analyzed_code_chunk,
    }
