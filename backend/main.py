"""FastAPI entry point."""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agent import CompanyNotFoundError
from backend.agent_graph import evaluate_with_graph
from backend.config import DEMO_QUERY
from backend.fallback import get_fallback_response, is_magic_query
from backend.schemas import ErrorResponse, EvaluateRequest, EvaluateResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FinSight AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # The API uses no cookies; credentials with a wildcard origin is rejected
    # by browsers and would be unsafe if auth were added later.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    try:
        return evaluate_with_graph(
            request.query,
            request.scenario_loan_amount,
            request.loan_amount,
            request.company_id,
        )
    except CompanyNotFoundError as exc:
        # A bad request, not an outage: say what is wrong instead of a 503.
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(message=str(exc), fallback_available=False).model_dump(),
        ) from exc
    except Exception as exc:
        logger.exception("Evaluation failed")
        if is_magic_query(request.query):
            return get_fallback_response()
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                message="The live reasoning service is temporarily unavailable.",
                fallback_available=is_magic_query(request.query),
            ).model_dump(),
        ) from exc


@app.get("/demo-query")
def demo_query() -> dict[str, str]:
    return {"query": DEMO_QUERY}
