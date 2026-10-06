from typing import Any, Literal

from pydantic import BaseModel, Field


class GoogleCredentialsPayload(BaseModel):
    credentials: dict[str, Any]


class PropertySelection(BaseModel):
    site_url: str = Field(min_length=3, max_length=2048)


class ImportRequest(BaseModel):
    days: int = Field(default=28, ge=7, le=180)
    row_limit: int = Field(default=25000, ge=1000, le=25000)
    max_rows: int = Field(default=50000, ge=1000, le=100000)


class TechnicalAuditRequest(BaseModel):
    days: int = Field(default=28, ge=7, le=180)
    max_pages: int = Field(default=50, ge=1, le=200)
    gsc_max_rows: int = Field(default=50000, ge=1000, le=100000)


class AssistantRunRequest(BaseModel):
    site_url: str | None = Field(default=None, max_length=2048)
    language: Literal["en", "fa"] = "en"


class MonitoredSiteUpdate(BaseModel):
    site_url: str = Field(min_length=3, max_length=2048)
    enabled: bool = True
    label: str = Field(default="", max_length=120)


class UrlInspectionRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)
    language: str = Field(default="en-US", min_length=2, max_length=20)


class AiExplainRequest(BaseModel):
    opportunity: dict[str, Any]
    language: Literal["en", "fa"] = "en"
    model: str | None = None
