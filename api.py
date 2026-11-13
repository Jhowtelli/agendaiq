from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from pathlib import Path

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")
DATA_FILE = Path(__file__).parent / "data" / "appointments.csv"
ALLOWED_SERVICES = {"corte", "barba", "coloracao", "manicure"}


def load_appointments() -> list[dict[str, str]]:
    with DATA_FILE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@function_tool
def analyze_booking_patterns(service: str = "todos") -> dict:
    """Return aggregated metrics from the synthetic appointments CSV."""
    rows = load_appointments()
    selected = rows if service == "todos" else [row for row in rows if row["service"] == service]
    completed = sum(row["status"] == "concluido" for row in selected)
    misses = sum(row["status"] == "falta" for row in selected)
    eligible = completed + misses
    by_service = defaultdict(Counter)
    by_weekday = defaultdict(Counter)
    for row in selected:
        by_service[row["service"]][row["status"]] += 1
        by_weekday[row["weekday"]][row["status"]] += 1
    return {
        "dataset": "synthetic appointments; 24 rows",
        "service_filter": service,
        "appointments": len(selected),
        "completed": completed,
        "cancellations": sum(row["status"] == "cancelado" for row in selected),
        "no_shows": misses,
        "no_show_rate_among_completed_or_missed_percent": round(100 * misses / eligible, 1) if eligible else 0,
        "by_service": {name: dict(counts) for name, counts in by_service.items()},
        "by_weekday": {name: dict(counts) for name, counts in by_weekday.items()},
    }


@function_tool
def compare_extra_slots(service: str, extra_slots: int) -> dict:
    """Estimate filled slots from the synthetic history; never creates appointments."""
    if service not in ALLOWED_SERVICES:
        return {"error": "Service is not in the synthetic allowlist."}
    slots = max(0, min(extra_slots, 12))
    rows = [row for row in load_appointments() if row["service"] == service]
    eligible = sum(row["status"] in {"concluido", "falta"} for row in rows)
    completed = sum(row["status"] == "concluido" for row in rows)
    fill_rate = completed / eligible if eligible else 0
    return {
        "dataset": "synthetic; illustrative calculation only",
        "service": service,
        "extra_slots_considered": slots,
        "historical_synthetic_fill_rate_percent": round(fill_rate * 100, 1),
        "illustrative_filled_slots": round(slots * fill_rate),
        "action_taken": False,
    }


demand_analyst = Agent(
    name="Analista de procura",
    model=MODEL,
    handoff_description="Analisa volume, faltas e distribuição por serviço ou dia.",
    instructions=(
        "Use analyze_booking_patterns. Descreva os dados como sintéticos, informe os "
        "denominadores das taxas e não extrapole os 24 registros como previsão real."
    ),
    tools=[analyze_booking_patterns],
)

capacity_planner = Agent(
    name="Planejador de capacidade",
    model=MODEL,
    handoff_description="Compara preenchimento ilustrativo de horários adicionais.",
    instructions=(
        "Use compare_extra_slots para qualquer estimativa numérica. Informe que o "
        "cálculo é ilustrativo e não cria, move ou confirma agendamentos."
    ),
    tools=[analyze_booking_patterns, compare_extra_slots],
)

retention_analyst = Agent(
    name="Analista de retenção",
    model=MODEL,
    handoff_description="Investiga padrões de faltas e cancelamentos no conjunto fictício.",
    instructions=(
        "Use as métricas agregadas. Sugira hipóteses para revisão humana, sem sugerir "
        "contato automático ou identificar pessoas."
    ),
    tools=[analyze_booking_patterns],
)

agenda_router = Agent(
    name="Coordenador AgendaIQ",
    model=MODEL,
    instructions=(
        "Encaminhe perguntas sobre procura para Analista de procura, horários para "
        "Planejador de capacidade e faltas/cancelamentos para Analista de retenção."
    ),
    handoffs=[demand_analyst, capacity_planner, retention_analyst],
)

app = FastAPI(title="AgendaIQ API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jhowtelli.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalysisRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "dataset": "synthetic"}


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest) -> dict[str, str]:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="Configure OPENAI_API_KEY no servidor local.")
    try:
        result = await Runner.run(agenda_router, request.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="A análise não foi concluída. Confira a configuração do modelo.") from exc
    return {
        "answer": str(result.final_output),
        "specialist": result.last_agent.name,
        "mode": "agents-sdk",
    }
