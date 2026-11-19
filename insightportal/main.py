from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from .warehouse import AS_OF, CONTRACT, DOMAINS, METRICS, ROOT, SITES, YEARS, Warehouse, dashboard_metric, quality
from .workflow import ACTORS, Conflict, InvalidDecision, MissingRequest, Workflow

log = logging.getLogger("insightportal")
Domain = Literal["finance", "commercial", "operations", "people"]
Month = Annotated[str, StringConstraints(pattern=r"^202[56]-(0[1-9]|1[0-2])$")]
Score = Annotated[int, Field(ge=1, le=5)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NewRequest(Input):
    domain: Domain
    title: Annotated[str, Field(min_length=8, max_length=96)]
    rationale: Annotated[str, Field(min_length=12, max_length=600)]
    requester: Literal["analyst", "finance-steward", "commercial-steward", "operations-steward", "people-steward"]
    kind: Literal["enhancement", "data-contract", "quality"]
    impact: Score
    urgency: Score
    effort: Score

    @field_validator("requester")
    @classmethod
    def analyst_submits(cls, actor, info):
        if actor != "analyst" and actor != f"{info.data.get('domain')}-steward":
            raise ValueError("Select the analyst or a steward from this request's domain")
        return actor


class Decision(Input):
    actor: str
    action: Literal["triage", "accept", "decline", "release"]
    note: Annotated[str, Field(min_length=12, max_length=400)]
    version: Annotated[int, Field(ge=1)]


class Feedback(Input):
    domain: Domain
    actor: Literal["analyst", "finance-steward", "commercial-steward", "operations-steward", "people-steward"]
    rating: Score


class Event(BaseModel):
    id: int
    request_id: int
    actor: str
    action: str
    note: str
    recorded_at: str


class BacklogItem(NewRequest):
    id: int
    state: str
    version: int
    score: int
    history: list[Event]


class Quality(BaseModel):
    id: Domain
    status: Literal["current", "late", "blocked"]
    checks: dict[str, bool]
    rows: int
    expected_rows: int
    published_at: str | None
    through_month: str | None
    age_hours: float | None
    sla_hours: int


class TrendPoint(BaseModel):
    month: str
    value: float | None


class BreakdownPoint(BaseModel):
    id: str
    value: float | None


class MetricResult(BaseModel):
    id: str
    value: float | None
    previous: float | None
    delta: float | None
    goal: float | None
    trend_goal: float | None
    trend: list[TrendPoint]
    sites: list[BreakdownPoint]


class Dashboard(BaseModel):
    scenario_as_of: str
    mode: Literal["local", "snowflake"]
    start: str
    end: str
    site: str | None
    quality: list[Quality]
    metrics: list[MetricResult]


class MetricDefinition(BaseModel):
    id: str
    name: str
    unit: Literal["EUR", "%", "count"]
    numerator: str
    denominator: str | None
    scale: float
    goal: float
    goal_basis: Literal["monthly_global", "period"]
    direction: Literal["up", "down"]
    definition: str
    formula: str
    exclusions: str


class Site(BaseModel):
    id: str
    name: str


class CohortRule(BaseModel):
    column: str
    minimum: int


class DomainDefinition(BaseModel):
    id: Domain
    name: str
    product: str
    owner: str
    consumer: str
    purpose: str
    table: str
    source: str
    freshness_hours: int
    checks: list[str]
    min_cohort: CohortRule | None
    metrics: list[MetricDefinition]


class SemanticContract(BaseModel):
    version: str
    scenario_as_of: str
    grain: list[str]
    shared_dimensions: list[str]
    sites: list[Site]
    domains: list[DomainDefinition]


class Catalog(BaseModel):
    contract: SemanticContract
    actors: dict[str, str]
    years: dict[str, int]


class FeedbackSummary(BaseModel):
    count: int
    average: float | None


class Adoption(BaseModel):
    id: Domain
    eligible: int
    active: int
    returning: int
    weeks: list[int]
    survey_count: int
    survey_average: float
    local_feedback: FeedbackSummary


def create_app(directory=None, mode=None):
    directory = Path(directory or os.environ.get("INSIGHTPORTAL_DATA_DIR", ROOT / "runtime"))
    warehouse = Warehouse(directory / "analytics.db", mode or os.environ.get("WAREHOUSE_MODE", "local"))
    workflow = Workflow(directory / "workflow.db")

    @asynccontextmanager
    async def lifespan(_):
        warehouse.initialize()
        workflow.initialize()
        yield

    app = FastAPI(title="InsightPortal", version=CONTRACT["version"], lifespan=lifespan)
    route = "/api/v1"

    @app.middleware("http")
    async def local_mutations(request: Request, call_next):
        if request.method in {"POST", "PATCH"} and request.url.path.startswith(route + "/"):
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
                return JSONResponse({"detail": "This action requires the portal's origin."}, status_code=403)
            content_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
            if content_type != "application/json":
                return JSONResponse({"detail": "Use application/json."}, status_code=415)
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": warehouse.mode}

    @app.get(route + "/catalog")
    def catalog() -> Catalog:
        return Catalog(contract=CONTRACT, actors=ACTORS, years=YEARS)

    @app.get(route + "/dashboard")
    def dashboard(
        start: Month = "2026-01", end: Month = "2026-09", site: str | None = None,
        domain: Domain | None = None,
        metrics: Annotated[list[str] | None, Query(max_length=8)] = None,
    ) -> Dashboard:
        if start > end or start[:4] != end[:4] or int(end[5:]) > YEARS[end[:4]]:
            raise HTTPException(422, "Select a published month range within a single calendar year.")
        if site is not None and site not in SITES:
            raise HTTPException(422, "Unknown service region.")
        if metrics is not None and (len(metrics) != len(set(metrics)) or any(
            key not in METRICS or (domain and METRICS[key][0]["id"] != domain) for key in metrics
        )):
            raise HTTPException(422, "Select distinct known metrics from the chosen domain.")
        groups = [DOMAINS[domain]] if domain else list(DOMAINS.values())
        quality_results, results = [], []
        try:
            with warehouse.connect() as connection:
                cursor = connection.cursor()
                if warehouse.mode == "local":
                    cursor.execute("BEGIN")
                for group in groups:
                    outcome = quality(cursor, group)
                    quality_results.append(outcome)
                    if outcome["status"] != "blocked":
                        results.extend(dashboard_metric(cursor, group, metric, start, end, site)
                                       for metric in group["metrics"] if metrics is None or metric["id"] in metrics)
                cursor.close()
        except Exception as exc:
            log.error("Analytics read failed (%s)", type(exc).__name__)
            raise HTTPException(503, "Analytics source unavailable. Retry when service is restored.") from exc
        return Dashboard(scenario_as_of=AS_OF.isoformat(), mode=warehouse.mode,
                         start=start, end=end, site=site, quality=quality_results, metrics=results)

    @app.get(route + "/requests")
    def list_requests() -> list[BacklogItem]:
        return workflow.list()

    @app.post(route + "/requests", status_code=201)
    def submit_request(body: NewRequest) -> BacklogItem:
        key = workflow.submit(body.model_dump())
        return next(row for row in workflow.list() if row["id"] == key)

    @app.post(route + "/requests/{key}/decisions")
    def decide_request(key: int, body: Decision) -> BacklogItem:
        try:
            workflow.decide(key, body.version, body.actor, body.action, body.note)
        except MissingRequest as exc:
            raise HTTPException(404, "Request not found.") from exc
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except InvalidDecision as exc:
            raise HTTPException(422, str(exc)) from exc
        return next(row for row in workflow.list() if row["id"] == key)

    @app.get(route + "/adoption")
    def adoption() -> list[Adoption]:
        return workflow.adoption()

    @app.post(route + "/adoption/feedback")
    def adoption_feedback(body: Feedback) -> Adoption:
        if body.actor not in {"analyst", f"{body.domain}-steward"}:
            raise HTTPException(422, "Select the analyst or this domain's steward.")
        workflow.feedback(body.domain, body.actor, body.rating)
        return next(row for row in workflow.adoption() if row["id"] == body.domain)

    dist = ROOT / "web/dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def home():
        if not (dist / "index.html").is_file():
            return JSONResponse({"message": "Build the web application to open the portal.", "openapi": "/docs"})
        return FileResponse(dist / "index.html")

    return app


app = create_app()
