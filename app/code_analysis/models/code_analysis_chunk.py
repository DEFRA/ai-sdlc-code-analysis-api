from typing import Optional

from pydantic import BaseModel


class CodeAnalysisChunk(BaseModel):
    """The data structure for the analyzed code chunks"""

    summary: str
    data_model: Optional[str] = None
    interfaces: Optional[str] = None
    business_logic: Optional[str] = None
    dependencies: Optional[str] = None
    configuration: Optional[str] = None
    infrastructure: Optional[str] = None
    non_functional: Optional[str] = None
