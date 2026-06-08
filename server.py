"""웹 서버 — LangGraph 에이전트를 HTTP API로 노출.

Railway/Fly.io/Render 같은 '항상 켜진' 서버에 배포하면 서버리스(Vercel)와 달리
요청 타임아웃이 없어, 리서치 파이프라인이 몇 분 걸려도 끝까지 돈다.

  POST /plan    : people 리스트를 받아 에이전트를 돌리고 결과 JSON 반환
  GET  /health  : 헬스체크 (배포 플랫폼이 사용)

로컬 실행:
  uvicorn server:app --reload --port 8000
"""
import logging
import os
import traceback

from dotenv import load_dotenv

load_dotenv()  # .env 읽기 (반드시 그래프 import 전)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel-agent")

from agent.graph import build_travel_agent

app = FastAPI(title="Travel Plan AI Agent")

# 프론트(Vercel)가 다른 도메인에서 호출하므로 CORS 허용.
# 운영에서는 ALLOWED_ORIGINS=https://your-app.vercel.app 로 좁히는 걸 권장.
_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 그래프는 한 번만 컴파일해 재사용 (요청마다 다시 만들 필요 없음).
_agent = build_travel_agent()


class Person(BaseModel):
    name: str
    available_dates: list[str] = []
    budget: int = 0
    energy_level: str = "medium"
    wishes: list[str] = []
    departure_city: str = ""
    hard_constraints: list[str] = []


class PlanRequest(BaseModel):
    people: list[Person]
    recursion_limit: int = 25


@app.get("/")
def root():
    return {
        "service": "Travel Plan AI Agent",
        "status": "running",
        "endpoints": {
            "POST /plan": "여행 계획 생성 — body: {\"people\": [...]}",
            "GET /health": "헬스체크",
            "GET /docs": "대화형 API 문서 (Swagger UI)",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan")
def plan(req: PlanRequest):
    initial = {
        "people": [p.model_dump() for p in req.people],
        "todos": [],
        "messages": [],
        "negotiate_attempts": 0,
    }
    try:
        final = _agent.invoke(initial, {"recursion_limit": req.recursion_limit})
    except Exception as e:  # noqa: BLE001 — 셋업 단계 디버깅용: 실제 에러를 노출
        logger.exception("agent invoke failed")
        return JSONResponse(
            status_code=500,
            content={"error": type(e).__name__, "detail": str(e),
                     "trace": traceback.format_exc().splitlines()[-8:]},
        )

    return {
        "chosen_dates": final.get("chosen_dates"),
        "chosen_destination": final.get("chosen_destination"),
        "chosen_coords": final.get("chosen_coords"),
        "destination_candidates": final.get("destination_candidates", []),
        "todos": final.get("todos", []),
        "research_results": final.get("research_results", {}),
        "awaiting_human": final.get("awaiting_human", False),
        "messages": final.get("messages", []),
    }
