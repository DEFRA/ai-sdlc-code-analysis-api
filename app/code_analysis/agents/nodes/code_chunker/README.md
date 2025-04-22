# Code Analyzer

A Python tool that analyzes Git repositories and chunks code based on features using tree-sitter and AWS Bedrock.

## Features

- Supports multiple programming languages (Python, JavaScript, TypeScript, C#, Java)
- Generates directory structure visualization
- Optional tree-sitter parsing for detailed code analysis
- Chunks code into logical feature groups using AWS Bedrock
- Provides a simple CLI interface

## Installation

Set up your AWS credentials and environment variables:

### Options

- `--repository-url`: URL of the Git repository to analyze (mutually exclusive with --repository-folder)
- `--repository-folder`: Absolute path to local repository folder to analyze (mutually exclusive with --repository-url)
- `--output`, `-o`: Output file path (default: analysis_result.json)
- `--pretty`, `-p`: Pretty print the output JSON
- `--log-prompts`: Log prompts sent to AWS Bedrock
- `--log-responses`: Log responses from AWS Bedrock
- `--log-file`: Path to the log file (default: bedrock_prompts.log)
- `--timeout`: Timeout in seconds for API calls (default: 120)
- `--verbose`, `-v`: Enable verbose (DEBUG level) logging
- `--exclude-tree-sitter`: Disable tree-sitter parsing for code elements (default: False)

## Output Format

The tool generates a JSON file containing:
- Repository URL
- File structure
- Languages used
- Code chunks grouped by features

Each code chunk includes:
- Chunk ID
- Description
- List of files
- Combined file contents
