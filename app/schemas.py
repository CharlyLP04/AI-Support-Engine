from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    ACCESS = "ACCESS"
    BUG = "BUG"
    FEATURE = "FEATURE"
    SECURITY = "SECURITY"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Mode(StrEnum):
    TRADITIONAL = "traditional"
    GENERATIVE = "generative"


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    mode: Mode

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class AnalysisResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: Category
    priority: Priority
    response: str = Field(min_length=1)
    requires_human_review: bool = Field(alias="requiresHumanReview")
    mode: Mode
