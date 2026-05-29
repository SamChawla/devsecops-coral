"""FastAPI backend for the devsecops-coral dashboard."""

from __future__ import annotations

import os
import sys

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:  # Sentry instrumentation is optional — the API boots without the SDK.
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    _SENTRY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when sentry-sdk is absent
    _SENTRY_AVAILABLE = False

from devsecops_coral.actions.executor import (
    ActionError,
    actions_response,
    approve_action,
    approve_all,
    dismiss_action,
    get_actions,
    load_actions,
)
from devsecops_coral.agent import AgentError, analyze_root_cause
from devsecops_coral.agent import ask as run_agent_ask
from devsecops_coral.auth import (
    AuthError,
    authenticate,
    create_session,
    delete_session,
    init_db,
    session_user,
)
from devsecops_coral.auth import signup as auth_signup
from devsecops_coral.config import (
    AUTH_ENABLED,
    GITHUB_OWNER,
    GITHUB_REPO,
    SENTRY_DSN,
    SENTRY_ENVIRONMENT,
    SENTRY_TRACES_SAMPLE_RATE,
    SESSION_TTL_HOURS,
    parse_packages,
    project_root,
)
from devsecops_coral.coral_client import (
    CoralError,
    add_bundled_source,
    add_custom_source,
    clear_query_cache,
    execute_query,
    get_sources_metadata,
    remove_source,
    split_sql_statements,
    test_source,
)
from devsecops_coral.integrations import get_integration, list_integrations
from devsecops_coral.models import (
    ActionsResponse,
    AskRequest,
    AskResponse,
    AuthResponse,
    CorrelateResponse,
    GithubPrsResponse,
    IntegrationInfo,
    IntegrationInputModel,
    IntegrationsResponse,
    LoginRequest,
    PostureResponse,
    RecommendedAction,
    RecommendResponse,
    RootCauseRequest,
    ScanResponse,
    SignupRequest,
    SourceActionResponse,
    SourceConnectRequest,
    SourceInfo,
    SourcesResponse,
    TimelineResponse,
)
from devsecops_coral.queries import (
    run_correlate,
    run_github_prs,
    run_posture,
    run_root_cause,
    run_scan,
    run_timeline,
)
from devsecops_coral.recommender import run_recommend


def _sentry_enabled() -> bool:
    """Return True only when Sentry should be initialised for this process.

    Sentry is skipped during test runs so unit tests never ship synthetic
    error events to a real Sentry project, and is opt-out via
    ``DEVSECOPS_DISABLE_SENTRY``.
    """
    if not (SENTRY_DSN and _SENTRY_AVAILABLE):
        return False
    if os.getenv("DEVSECOPS_DISABLE_SENTRY"):
        return False
    if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return False
    return True


if _sentry_enabled():
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        environment=SENTRY_ENVIRONMENT,
        release="devsecops-coral@0.1.0",
    )

app = FastAPI(
    title="devsecops-coral",
    description="Cross-stack security correlation powered by Coral SQL",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = project_root() / "frontend" / "dist"

SESSION_COOKIE = "coral_session"
_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip().lower() in ("1", "true", "yes")

if AUTH_ENABLED:
    init_db()


def _set_session_cookie(response: Response, token: str) -> None:
    """Attach the httpOnly session cookie to a response."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
        path="/",
    )


def require_user(request: Request) -> dict:
    """Dependency: resolve the current user from the session cookie.

    When auth is disabled (``DEVSECOPS_AUTH_ENABLED=0``) this is a no-op so the
    CLI/dev workflows keep working. Otherwise an invalid/missing session yields
    HTTP 401.
    """
    if not AUTH_ENABLED:
        return {"user": None, "org": None}
    data = session_user(request.cookies.get(SESSION_COOKIE))
    if not data:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return data


def _coral_http_error(exc: Exception) -> HTTPException:
    """Map Coral/agent errors to HTTP 502."""
    return HTTPException(status_code=502, detail=str(exc))


@app.post("/api/auth/signup", response_model=AuthResponse)
def api_signup(body: SignupRequest, response: Response) -> AuthResponse:
    """Create an organization + owner user and start a session."""
    try:
        result = auth_signup(body.email, body.password, body.org_name)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, create_session(result["user"]["id"]))
    return AuthResponse(**result)


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(body: LoginRequest, response: Response) -> AuthResponse:
    """Authenticate an existing user and start a session."""
    try:
        result = authenticate(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, create_session(result["user"]["id"]))
    return AuthResponse(**result)


@app.post("/api/auth/logout", response_model=AuthResponse)
def api_logout(request: Request, response: Response) -> AuthResponse:
    """End the current session and clear the cookie."""
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return AuthResponse()


@app.get("/api/auth/me", response_model=AuthResponse)
def api_me(request: Request) -> AuthResponse:
    """Return the currently authenticated identity (null fields when anonymous)."""
    if not AUTH_ENABLED:
        return AuthResponse()
    data = session_user(request.cookies.get(SESSION_COOKIE))
    return AuthResponse(**data) if data else AuthResponse()


def _source_status_list() -> list[SourceInfo]:
    """Return the normalized source status list used across source endpoints."""
    metadata, _sql = get_sources_metadata()
    return [SourceInfo(**item) for item in metadata]


def _integration_catalog() -> list[IntegrationInfo]:
    """Return integration metadata enriched with connection status."""
    source_map = {source.name: source for source in _source_status_list()}
    catalog: list[IntegrationInfo] = []
    for integration in list_integrations():
        if integration.kind == "planned":
            continue
        source = source_map.get(integration.name)
        catalog.append(
            IntegrationInfo(
                name=integration.name,
                kind=integration.kind,
                description=integration.description,
                docs_url=integration.docs_url,
                connected=source.connected if source else False,
                table_count=source.table_count if source else 0,
                mode=source.mode if source else "cli",
                inputs=[
                    IntegrationInputModel(
                        key=item.key,
                        label=item.label,
                        required=item.required,
                        secret=item.secret,
                        placeholder=item.placeholder,
                        help_text=item.help_text,
                        default=item.default,
                    )
                    for item in integration.inputs
                ],
            )
        )
    return catalog


def _validated_source_values(body: SourceConnectRequest) -> tuple[str, dict[str, str]]:
    """Validate UI-provided source credentials before invoking Coral."""
    integration = get_integration(body.name)
    if integration.kind == "planned":
        raise HTTPException(
            status_code=400, detail=f"{integration.name} is planned but not implemented yet."
        )

    values = {key: value.strip() for key, value in body.values.items() if value and value.strip()}
    missing = [
        item.label for item in integration.inputs if item.required and not values.get(item.key)
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}.",
        )
    return integration.name, values


@app.get("/api/scan", response_model=ScanResponse, dependencies=[Depends(require_user)])
def api_scan(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,requests,pillow,celery"),
    refresh: bool = Query(default=False),
) -> ScanResponse:
    """Return vulnerability scan results and the Coral SQL used."""
    if refresh:
        clear_query_cache()
    try:
        pkg_list = parse_packages(packages)
        result = run_scan(ecosystem=ecosystem, packages=pkg_list)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc
    return ScanResponse(
        data=result.data,
        sql=result.sql,
        ecosystem=ecosystem,
        packages=pkg_list,
    )


@app.get("/api/correlate", response_model=CorrelateResponse, dependencies=[Depends(require_user)])
def api_correlate(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,requests,pillow,celery"),
    since: str = Query(default="7d"),
    refresh: bool = Query(default=False),
) -> CorrelateResponse:
    """Return vulnerability-error correlations and the Coral SQL used."""
    if refresh:
        clear_query_cache()
    try:
        pkg_list = parse_packages(packages)
        result = run_correlate(ecosystem=ecosystem, packages=pkg_list, since=since)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc
    return CorrelateResponse(
        data=result.data,
        sql=result.sql,
        since=since,
        ecosystem=ecosystem,
        packages=pkg_list,
    )


@app.get("/api/timeline", response_model=TimelineResponse, dependencies=[Depends(require_user)])
def api_timeline(
    since: str = Query(default="24h"),
    github_owner: str | None = Query(default=None),
    github_repo: str | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> TimelineResponse:
    """Return unified event timeline and the Coral SQL used."""
    if refresh:
        clear_query_cache()
    try:
        result = run_timeline(since=since, owner=github_owner, repo=github_repo)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc
    return TimelineResponse(data=result.data, sql=result.sql, since=since)


@app.get("/api/github-prs", response_model=GithubPrsResponse, dependencies=[Depends(require_user)])
def api_github_prs(
    github_owner: str | None = Query(default=None),
    github_repo: str | None = Query(default=None),
    since: str = Query(default="90d"),
    state: str | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> GithubPrsResponse:
    """Return security-related GitHub PRs for the repo and the Coral SQL used."""
    if refresh:
        clear_query_cache()
    try:
        result = run_github_prs(owner=github_owner, repo=github_repo, since=since, state=state)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc
    return GithubPrsResponse(
        data=result.data,
        sql=result.sql,
        owner=(github_owner or GITHUB_OWNER or ""),
        repo=(github_repo or GITHUB_REPO or ""),
        since=since,
    )


@app.post("/api/ask", response_model=AskResponse, dependencies=[Depends(require_user)])
def api_ask(body: AskRequest) -> AskResponse:
    """Agent: natural language to SQL to results to analysis, plus best-effort recommendations."""
    try:
        result = run_agent_ask(body.query)
    except (AgentError, CoralError) as exc:
        raise _coral_http_error(exc) from exc

    recommendations = [
        RecommendedAction(**r) if isinstance(r, dict) else r
        for r in result.get("recommendations", [])
    ]
    return AskResponse(
        data=result["rows"],
        sql=result["sql"],
        analysis=result["analysis"],
        question=result["question"],
        row_count=result["row_count"],
        recommendations=recommendations,
    )


@app.post("/api/root-cause", response_model=AskResponse, dependencies=[Depends(require_user)])
def api_root_cause(body: RootCauseRequest) -> AskResponse:
    """Root-cause a CVE: join OSV + Sentry errors + related GitHub PRs, then narrate.

    Returns the same shape as /api/ask (data + sql + analysis) so the dashboard's
    Query Console can render the result with no extra plumbing.
    """
    try:
        result = run_root_cause(
            ecosystem=body.ecosystem,
            package=body.package,
            cve=body.cve,
            since=body.since,
        )
        analysis = analyze_root_cause(cve=body.cve, package=body.package, rows=result.data)
    except (AgentError, CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc

    target = body.cve or body.package
    return AskResponse(
        data=result.data,
        sql=result.sql,
        analysis=analysis,
        question=f"Root cause for {target}",
        row_count=len(result.data),
    )


@app.post("/api/sql", response_model=AskResponse, dependencies=[Depends(require_user)])
def api_raw_sql(body: AskRequest) -> AskResponse:
    """Execute raw Coral SQL (SELECT only).

    Coral runs one statement at a time, but the scan/correlate SQL shown in the
    viewer is several per-package statements joined with ``;``. We split on
    top-level semicolons and run each statement, concatenating the rows so that
    pasting the generated SQL works as expected.
    """
    sql = body.query.strip()
    statements = split_sql_statements(sql)
    if not statements:
        raise HTTPException(status_code=400, detail="No SQL statement provided.")
    for stmt in statements:
        if not stmt.upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")

    rows: list[dict] = []
    try:
        for stmt in statements:
            rows.extend(execute_query(stmt))
    except CoralError as exc:
        raise _coral_http_error(exc) from exc

    suffix = f" across {len(statements)} statements" if len(statements) > 1 else ""
    return AskResponse(
        data=rows,
        sql=sql,
        analysis=f"Query returned {len(rows)} row(s){suffix}.",
        question=sql,
        row_count=len(rows),
    )


@app.get("/api/sources", response_model=SourcesResponse, dependencies=[Depends(require_user)])
def api_sources() -> SourcesResponse:
    """Return connected source status with table counts."""
    metadata, sql = get_sources_metadata()
    return SourcesResponse(
        sources=[SourceInfo(**item) for item in metadata],
        sql=sql,
    )


@app.get(
    "/api/integrations",
    response_model=IntegrationsResponse,
    dependencies=[Depends(require_user)],
)
def api_integrations() -> IntegrationsResponse:
    """Return the integration catalog with current connection status."""
    return IntegrationsResponse(integrations=_integration_catalog())


@app.post(
    "/api/sources/connect",
    response_model=SourceActionResponse,
    dependencies=[Depends(require_user)],
)
def api_connect_source(body: SourceConnectRequest) -> SourceActionResponse:
    """Connect or update a Coral source using UI-provided credentials."""
    try:
        name, values = _validated_source_values(body)
        integration = get_integration(name)
        if integration.kind == "custom":
            if not integration.spec_path:
                raise HTTPException(
                    status_code=400, detail=f"No source spec registered for {name}."
                )
            add_custom_source(str(integration.spec_path), env=values)
        else:
            add_bundled_source(name, interactive=False, env=values)
    except HTTPException:
        raise
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc

    return SourceActionResponse(
        source=name,
        message=f"{name} connected successfully.",
        sources=_source_status_list(),
    )


@app.post(
    "/api/sources/{name}/test",
    response_model=SourceActionResponse,
    dependencies=[Depends(require_user)],
)
def api_test_source(name: str) -> SourceActionResponse:
    """Run Coral validation for an installed source."""
    try:
        test_source(name)
    except CoralError as exc:
        raise _coral_http_error(exc) from exc
    return SourceActionResponse(
        source=name,
        message=f"{name} validated successfully.",
        sources=_source_status_list(),
    )


@app.delete(
    "/api/sources/{name}",
    response_model=SourceActionResponse,
    dependencies=[Depends(require_user)],
)
def api_remove_source(name: str) -> SourceActionResponse:
    """Remove an installed source."""
    try:
        remove_source(name)
    except CoralError as exc:
        raise _coral_http_error(exc) from exc
    return SourceActionResponse(
        source=name,
        message=f"{name} removed successfully.",
        sources=_source_status_list(),
    )


@app.get("/api/posture", response_model=PostureResponse, dependencies=[Depends(require_user)])
def api_posture(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,requests,pillow,celery"),
    refresh: bool = Query(default=False),
) -> PostureResponse:
    """Return aggregated severity counts and untracked CVE count."""
    if refresh:
        clear_query_cache()
    try:
        return run_posture(ecosystem=ecosystem, packages=packages)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc


@app.get("/api/recommend", response_model=RecommendResponse, dependencies=[Depends(require_user)])
def api_recommend(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,flask,requests,celery,pillow"),
    since: str = Query(default="7d"),
    refresh: bool = Query(default=False),
) -> RecommendResponse:
    """Run scan + correlate and return ordered agent action recommendations."""
    if refresh:
        clear_query_cache()
    try:
        return run_recommend(ecosystem=ecosystem, packages=packages, since=since)
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc


@app.post("/api/recommend", response_model=RecommendResponse, dependencies=[Depends(require_user)])
def api_recommend_regenerate(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,flask,requests,celery,pillow"),
    since: str = Query(default="7d"),
) -> RecommendResponse:
    """Regenerate recommendations and refresh the in-memory action store."""
    try:
        result = run_recommend(ecosystem=ecosystem, packages=packages, since=since)
        load_actions(result.actions)
        return result
    except (CoralError, ValueError) as exc:
        raise _coral_http_error(exc) from exc


@app.get("/api/actions", response_model=ActionsResponse, dependencies=[Depends(require_user)])
def api_get_actions(
    ecosystem: str = Query(default="PyPI"),
    packages: str = Query(default="django,flask,requests,celery,pillow"),
    refresh: bool = Query(default=False),
) -> ActionsResponse:
    """Return current action list; auto-populates from recommend when empty.

    With ``refresh=true`` the Coral cache is busted and recommendations are
    regenerated. Otherwise an already-populated store is returned as-is, and a
    cold store reuses the cached scan/correlate reads from the Detect tab.
    """
    if refresh:
        clear_query_cache()
    if refresh or not get_actions():
        try:
            result = run_recommend(ecosystem=ecosystem, packages=packages)
            load_actions(result.actions)
        except (CoralError, ValueError):
            pass
    return actions_response()


@app.post(
    "/api/actions/{action_id}/approve",
    response_model=RecommendedAction,
    dependencies=[Depends(require_user)],
)
def api_approve_action(action_id: int) -> RecommendedAction:
    """Approve and execute a single pending action."""
    try:
        return approve_action(action_id)
    except ActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/actions/approve-all",
    response_model=ActionsResponse,
    dependencies=[Depends(require_user)],
)
def api_approve_all() -> ActionsResponse:
    """Approve and execute all pending actions sequentially."""
    approve_all()
    return actions_response()


@app.post(
    "/api/actions/{action_id}/dismiss",
    response_model=RecommendedAction,
    dependencies=[Depends(require_user)],
)
def api_dismiss_action(action_id: int) -> RecommendedAction:
    """Dismiss a pending action without executing it."""
    try:
        return dismiss_action(action_id)
    except ActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.exception_handler(404)
    async def spa_404_handler(request: Request, exc: HTTPException) -> FileResponse | JSONResponse:
        """Serve the SPA for non-API 404 routes; avoids catch-all GET route conflicts."""
        if request.url.path.startswith("/api"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)
