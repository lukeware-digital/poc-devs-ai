import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from main import DEVsAISystem

logger = logging.getLogger("DEVs_AI")

app = FastAPI(title="DEVs AI API", version="1.0.0")
system: Optional[DEVsAISystem] = None


class ProcessRequest(BaseModel):
    user_input: str


class ProcessResponse(BaseModel):
    success: bool
    execution_time: float
    timestamp: str
    result: Optional[dict] = None
    error: Optional[str] = None
    recovery_suggestions: Optional[list] = None


@app.on_event("startup")
async def startup_event():
    global system
    from utils.hardware_detection import detect_hardware_profile

    hardware_profile = detect_hardware_profile()
    config_path = f"config/hardware_profiles/{hardware_profile}.yaml"

    system = DEVsAISystem(config_path)
    try:
        await system.initialize()
        logger.info("Sistema DEVs AI inicializado via API")
    except Exception as e:
        logger.error(f"Falha na inicialização do sistema: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    global system
    if system:
        logger.info("Encerrando sistema DEVs AI")
    system = None


@app.post("/api/process", response_model=ProcessResponse)
async def process_request(request: ProcessRequest):
    if not system or not system.is_initialized:
        raise HTTPException(status_code=503, detail="Sistema não inicializado")

    if not request.user_input or not request.user_input.strip():
        raise HTTPException(status_code=400, detail="Solicitação não pode estar vazia")

    try:
        timeout = system.config.get("orchestrator", {}).get("request_timeout", 600)
        result = await asyncio.wait_for(
            system.process_request(request.user_input),
            timeout=timeout,
        )
        return ProcessResponse(
            success=result.get("success", False),
            execution_time=result.get("execution_time", 0),
            timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat()),
            result=result if result.get("success") else None,
            error=result.get("error"),
            recovery_suggestions=result.get("recovery_suggestions"),
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout na solicitação após {timeout}s")
        return ProcessResponse(
            success=False,
            execution_time=timeout,
            timestamp=datetime.now(timezone.utc).isoformat(),
            error=f"Processamento excedeu o tempo limite de {timeout} segundos",
            recovery_suggestions=[
                "A solicitação pode ser muito complexa",
                "Tente dividir em solicitações menores",
                "Verifique se os serviços estão respondendo corretamente",
            ],
        )
    except Exception as e:
        logger.error(f"Erro ao processar solicitação: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/api/status")
async def get_status():
    if not system:
        return JSONResponse(
            status_code=503,
            content={"status": "not_initialized", "message": "Sistema não inicializado"},
        )

    try:
        status = system.get_system_status()
        return {
            "status": "operational" if system.is_initialized else "initializing",
            "initialized": system.is_initialized,
            "agents_ready": status.get("agents_ready", []),
            "services": status.get("services", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.get("/api/metrics")
async def get_metrics():
    if not system or not system.metrics_collector:
        raise HTTPException(status_code=503, detail="Sistema ou coletor de métricas não disponível")

    try:
        metrics = {}
        for agent_id in system.orchestrator.agents.keys():
            agent = system.orchestrator.agents[agent_id]
            metrics[agent_id] = agent.get_metrics()

        system_metrics = {
            "total_agents": len(system.orchestrator.agents),
            "agent_metrics": metrics,
            "alerts": system.metrics_collector.alerts[-10:] if hasattr(system.metrics_collector, "alerts") else [],
        }

        return {
            "metrics": system_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


@app.get("/")
async def root():
    return {
        "service": "DEVs AI API",
        "version": "1.0.0",
        "endpoints": {
            "process": "/api/process",
            "status": "/api/status",
            "metrics": "/api/metrics",
        },
    }

