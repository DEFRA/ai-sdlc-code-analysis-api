from typing import Optional

from pydantic import BaseModel, Field


class CodeAnalysisChunk(BaseModel):
    """The data structure for the analyzed code chunks"""

    chunk_id: str = Field(..., description="The unique identifier")
    summary: str = Field(..., description="Summary of the code chunk")
    data_model: Optional[str] = Field(
        None, description="Data model information in the chunk"
    )
    interfaces: Optional[str] = Field(
        None, description="Interface definitions in the chunk"
    )
    business_logic: Optional[str] = Field(
        None, description="Business logic in the chunk"
    )
    dependencies: Optional[str] = Field(
        None, description="Dependencies used in the chunk"
    )
    configuration: Optional[str] = Field(
        None, description="Configuration details in the chunk"
    )
    infrastructure: Optional[str] = Field(
        None, description="Infrastructure code in the chunk"
    )
    non_functional: Optional[str] = Field(
        None, description="Non-functional aspects in the chunk"
    )
