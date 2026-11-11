from pydantic import BaseModel, Field


class GapList(BaseModel):
    items: list[dict]
    total: int


class GapAnnotation(BaseModel):
    annotation: str = Field(min_length=1, max_length=500)
