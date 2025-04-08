from pydantic import BaseModel


class CodeChunk(BaseModel):
    """A chunk of code from the repository."""

    chunk_id: str
    description: str
    files: list[str]
    content: str


class RepositoryAnalysis(BaseModel):
    """Analysis results for a repository."""

    repository_url: str
    file_structure: str
    languages_used: list[str]
    ingested_repo_chunks: list[CodeChunk]
