"""Pydantic models for query results and API responses."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result from a Coral query runner."""

    data: list[dict[str, Any]]
    sql: str


class ScanResponse(BaseModel):
    """Response for GET /api/scan."""

    data: list[dict[str, Any]]
    sql: str
    ecosystem: str
    packages: list[str]


class CorrelateResponse(BaseModel):
    """Response for GET /api/correlate."""

    data: list[dict[str, Any]]
    sql: str
    since: str
    ecosystem: str
    packages: list[str]


class TimelineResponse(BaseModel):
    """Response for GET /api/timeline."""

    data: list[dict[str, Any]]
    sql: str
    since: str


class GithubPrsResponse(BaseModel):
    """Response for GET /api/github-prs."""

    data: list[dict[str, Any]]
    sql: str
    owner: str
    repo: str
    since: str


class AskRequest(BaseModel):
    """Request body for POST /api/ask."""

    query: str = Field(min_length=1)


class RootCauseRequest(BaseModel):
    """Request body for POST /api/root-cause."""

    package: str = Field(min_length=1)
    cve: str | None = None
    ecosystem: str = "PyPI"
    since: str = "30d"


class ActionType(str, Enum):
    """Type of recommended remediation action."""

    CREATE_JIRA = "create_jira"
    CREATE_PR = "create_pr"
    CREATE_GITHUB_ISSUE = "create_github_issue"
    ANNOTATE_GRAFANA = "annotate_grafana"
    GENERATE_REPORT = "generate_report"


class ActionStatus(str, Enum):
    """Lifecycle state of a recommended action."""

    PENDING = "pending"
    EXECUTING = "executing"
    DONE = "done"
    DISMISSED = "dismissed"
    FAILED = "failed"


class RecommendedAction(BaseModel):
    """A single agent-recommended remediation action awaiting approval."""

    id: int
    type: ActionType
    status: ActionStatus = ActionStatus.PENDING
    title: str
    detail: str
    cve: str | None = None
    package: str | None = None
    severity: str = "INFO"
    urgent: bool = False
    result: dict[str, Any] | None = None


class RecommendResponse(BaseModel):
    """Response for GET /api/recommend and POST /api/recommend."""

    actions: list[RecommendedAction]
    ecosystem: str
    packages: list[str]


class ActionsResponse(BaseModel):
    """Response for GET /api/actions and POST /api/actions/approve-all."""

    actions: list[RecommendedAction]
    pending: int = 0
    executing: int = 0
    done: int = 0
    dismissed: int = 0
    failed: int = 0


class AskResponse(BaseModel):
    """Response for POST /api/ask."""

    data: list[dict[str, Any]]
    sql: str
    analysis: str
    question: str
    row_count: int
    recommendations: list[RecommendedAction] = Field(default_factory=list)


class SourceInfo(BaseModel):
    """Status for a single Coral data source."""

    name: str
    connected: bool
    table_count: int = 0
    mode: str = "cli"


class SourcesResponse(BaseModel):
    """Response for GET /api/sources."""

    sources: list[SourceInfo]
    sql: str


class IntegrationInputModel(BaseModel):
    """Serializable input metadata for a source connection form."""

    key: str
    label: str
    required: bool = True
    secret: bool = False
    placeholder: str = ""
    help_text: str = ""
    default: str = ""


class IntegrationInfo(BaseModel):
    """Dashboard-facing integration catalog entry."""

    name: str
    kind: str
    description: str
    docs_url: str = ""
    connected: bool = False
    table_count: int = 0
    mode: str = "cli"
    inputs: list[IntegrationInputModel] = Field(default_factory=list)


class IntegrationsResponse(BaseModel):
    """Response for GET /api/integrations."""

    integrations: list[IntegrationInfo]


class SourceConnectRequest(BaseModel):
    """Request body for connecting or updating a source."""

    name: str = Field(min_length=1)
    values: dict[str, str] = Field(default_factory=dict)


class SourceActionResponse(BaseModel):
    """Response for connect/test/remove source actions."""

    ok: bool = True
    source: str
    message: str
    sources: list[SourceInfo] = Field(default_factory=list)


class PostureResponse(BaseModel):
    """Response for GET /api/posture."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0
    untracked: int = 0
    total: int = 0
    sql: str
    ecosystem: str
    packages: list[str]


class OrgInfo(BaseModel):
    """Public organization fields exposed to the client."""

    id: int
    name: str


class UserInfo(BaseModel):
    """Public user fields exposed to the client."""

    id: int
    email: str
    role: str


class AuthResponse(BaseModel):
    """Response for /api/auth/* — the resolved identity (null when anonymous)."""

    user: UserInfo | None = None
    org: OrgInfo | None = None


class SignupRequest(BaseModel):
    """Request body for POST /api/auth/signup."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    org_name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
