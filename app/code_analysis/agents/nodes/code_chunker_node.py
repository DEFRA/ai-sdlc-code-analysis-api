"""
Node implementation for code chunking functionality.
"""

from logging import getLogger

from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.code_analysis.models.code_analysis import CodeChunk

logger = getLogger(__name__)


async def code_chunker(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Analyze the repository and populate state with code chunks.
    Currently using canned/placeholder data.
    """
    logger.info("Analyzing code repository: %s", state.repo_url)
    logger.info("Initial state: %s", state.model_dump())

    # Populate with canned data for now
    state.file_structure = """
    /
    ├── src/
    │   ├── main.py
    │   ├── utils/
    │   │   ├── helpers.py
    │   │   └── formatting.py
    │   └── models/
    │       └── data_models.py
    ├── tests/
    │   └── test_main.py
    ├── README.md
    └── requirements.txt
    """

    state.languages_used = ["Python", "Markdown"]

    state.ingested_repo_chunks = [
        CodeChunk(
            chunk_id="chunk1",
            description="Main application code",
            files=["src/main.py"],
            content="def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()",
        ),
        CodeChunk(
            chunk_id="chunk2",
            description="Utility functions",
            files=["src/utils/helpers.py", "src/utils/formatting.py"],
            content="def format_text(text):\n    return text.strip()\n\ndef is_valid(data):\n    return data is not None",
        ),
        CodeChunk(
            chunk_id="chunk3",
            description="Data models",
            files=["src/models/data_models.py"],
            content="class User:\n    def __init__(self, name):\n        self.name = name",
        ),
    ]

    # Log updated state
    logger.info("Updated state: %s", state.model_dump())
    logger.info("Completed code analysis for repository: %s", state.repo_url)
    return state
