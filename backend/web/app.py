"""실행: python -m uvicorn backend.web.app:app --host 127.0.0.1 --no-access-log"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .schemas import SimulationInput, SimulationResponse
from .service import simulate
from .comparison_schemas import ComparisonInput, ComparisonResponse
from .comparison import compare_scenarios
from .savings import RecurringSavingsRequest,RecurringSavingsResponse,simulate_recurring_savings
from .products import router as products_router
from .product_discovery import router as discovery_router
from .savings_matching import router as matching_router
from .asset_programs import router as asset_programs_router
from .explanations import router as explanations_router
from .asset_alerts import router as alerts_router, lifespan

app = FastAPI(title="청년 경제생활 · 합성 시연", version="m3.0", lifespan=lifespan)
app.include_router(products_router)
app.include_router(discovery_router)
app.include_router(matching_router)
app.include_router(asset_programs_router)
app.include_router(explanations_router)
app.include_router(alerts_router)


@app.middleware("http")
async def prevent_response_storage(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError):
    # 기본 오류의 input/context에 포함될 수 있는 소득·지출 원문은 응답하지 않는다.
    errors = [{"loc": list(error["loc"]), "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "입력 형식과 범위를 확인해 주세요.", "errors": errors})


@app.get("/api/health")
def health():
    return {"status": "ok", "synthetic": True, "test_only": True}


@app.post("/api/synthetic/simulate", response_model=SimulationResponse)
def simulation(data: SimulationInput):
    return simulate(data)


@app.post("/api/synthetic/compare", response_model=ComparisonResponse)
def comparison(data: ComparisonInput):
    return compare_scenarios(data)


@app.post('/api/synthetic/savings/recurring',response_model=RecurringSavingsResponse)
def recurring_savings(data:RecurringSavingsRequest):
    return simulate_recurring_savings(data)



# Production-only static hosting and public-origin configuration.
from .hosting import configure_production
configure_production(app)
