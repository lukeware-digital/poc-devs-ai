import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from main import DEVsAISystem
from models.job_model import JobRequest, JobStatus, JobResponse, CommitApprovalRequest
from services.job_processor import JobProcessor
from services.job_manager import JobManager
from database.connection import DatabaseConnection
from utils.git_utils import create_archive

logger = logging.getLogger("DEVs_AI")

app = FastAPI(title="DEVs AI API", version="1.0.0")
system: Optional[DEVsAISystem] = None
job_processor: Optional[JobProcessor] = None
job_manager: Optional[JobManager] = None


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
    global system, job_processor, job_manager
    from utils.hardware_detection import detect_hardware_profile

    hardware_profile = detect_hardware_profile()
    config_path = f"config/hardware_profiles/{hardware_profile}.yaml"

    system = DEVsAISystem(config_path)
    try:
        await system.initialize()
        await DatabaseConnection.initialize()
        
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "database" / "migrations" / "001_create_jobs_table.sql"
        if migration_path.exists():
            pool = await DatabaseConnection.get_pool()
            async with pool.acquire() as conn:
                migration_sql = migration_path.read_text()
                await conn.execute(migration_sql)
                logger.info("Migração do banco de dados executada com sucesso")
        
        job_processor = JobProcessor(system)
        job_manager = JobManager()
        logger.info("Sistema DEVs AI inicializado via API")
    except Exception as e:
        logger.error(f"Falha na inicialização do sistema: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    global system, job_processor, job_manager
    if system:
        logger.info("Encerrando sistema DEVs AI")
        try:
            if system.orchestrator and hasattr(system.orchestrator, 'llm_layer'):
                if hasattr(system.orchestrator.llm_layer, 'providers'):
                    for provider in system.orchestrator.llm_layer.providers:
                        if hasattr(provider, 'client') and hasattr(provider.client, 'close'):
                            try:
                                await provider.client.close()
                            except Exception as e:
                                logger.warning(f"Erro ao fechar cliente LLM: {str(e)}")
                        if hasattr(provider, 'session') and provider.session:
                            try:
                                if not provider.session.closed:
                                    await provider.session.close()
                            except Exception as e:
                                logger.warning(f"Erro ao fechar sessão LLM: {str(e)}")
        except Exception as e:
            logger.warning(f"Erro durante cleanup de recursos LLM: {str(e)}")
    await DatabaseConnection.close()
    system = None
    job_processor = None
    job_manager = None


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


@app.post("/api/jobs/start", response_model=JobResponse)
async def start_job(request: JobRequest):
    if not system or not system.is_initialized:
        raise HTTPException(status_code=503, detail="Sistema não inicializado")
    if not job_processor or not job_manager:
        raise HTTPException(status_code=503, detail="Job processor não inicializado")

    try:
        job_data = {
            "status": "pending",
            "repository_url": request.repository_url,
            "project_path": request.project_path,
            "user_input": request.user_input,
            "progress": 0.0,
            "current_step": "Criando job",
        }
        job_id = await job_manager.create_job(job_data)

        task = asyncio.create_task(job_processor.process_job(job_id, request))
        job_manager.register_active_job(job_id, task)

        return JobResponse(
            job_id=job_id,
            status="pending",
            message="Job criado e iniciado com sucesso",
        )
    except Exception as e:
        logger.error(f"Erro ao iniciar job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar job: {str(e)}")


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: UUID):
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job manager não inicializado")

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return JobStatus(**job)


@app.get("/api/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job manager não inicializado")

    jobs = await job_manager.list_jobs(status, limit, offset)
    return {"jobs": jobs, "total": len(jobs)}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: UUID):
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job manager não inicializado")

    try:
        await job_manager.cancel_job(job_id)
        return {"success": True, "message": "Job cancelado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao cancelar job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar job: {str(e)}")


@app.post("/api/jobs/{job_id}/approve-commit")
async def approve_commit(job_id: UUID, request: CommitApprovalRequest):
    if not job_processor:
        raise HTTPException(status_code=503, detail="Job processor não inicializado")

    try:
        result = await job_processor.approve_commit(job_id, request.approved, request.commit_message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao aprovar commit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao aprovar commit: {str(e)}")


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: UUID):
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job manager não inicializado")

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    project_path = job.get("project_path")
    if not project_path:
        raise HTTPException(status_code=404, detail="Caminho do projeto não encontrado")

    try:
        archive_path = create_archive(project_path)
        return FileResponse(
            archive_path,
            media_type="application/zip",
            filename=f"job_{job_id}.zip",
        )
    except Exception as e:
        logger.error(f"Erro ao criar arquivo para download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivo: {str(e)}")


@app.get("/")
async def root():
    return {
        "service": "DEVs AI API",
        "version": "1.0.0",
        "endpoints": {
            "process": "/api/process",
            "status": "/api/status",
            "metrics": "/api/metrics",
            "jobs": {
                "start": "/api/jobs/start",
                "get": "/api/jobs/{job_id}",
                "list": "/api/jobs",
                "cancel": "/api/jobs/{job_id}/cancel",
                "approve_commit": "/api/jobs/{job_id}/approve-commit",
                "download": "/api/jobs/{job_id}/download",
            },
        },
    }

