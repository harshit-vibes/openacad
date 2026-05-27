from datetime import datetime

from pydantic import BaseModel, Field


class PaperSource(BaseModel):
    id: str
    filename: str
    title: str | None = None
    uploaded_at: datetime
    n_pages: int
    n_chunks: int = 0


class Chunk(BaseModel):
    id: str
    source_id: str
    ordinal: int
    text: str
    page_range: tuple[int, int]
    char_range: tuple[int, int] = (0, 0)
    metadata: dict = Field(default_factory=dict)
