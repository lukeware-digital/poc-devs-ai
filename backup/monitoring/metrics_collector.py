"""
Coletor de Métricas - Coleta e analisa métricas de performance e saúde do sistema
"""

import json
import logging
from datetime import datetime, timedelta

import numpy as np
import psutil
import redis

logger = logging.getLogger("devs-ai")


class MetricsCollector:
    """
    Coletor de métricas do sistema com anomalia detection e alerting
    """

    def __init__(self, config: dict[str, any]):
        self.config = config
        self.metrics_history = {}
        self.alerts = []
        self.start_time = datetime.utcnow()
        self.last_gc_time = datetime.utcnow()
        self.last_alerts_cleanup = datetime.utcnow()
        self.max_alerts = 1000  # Limite de alertas em memória
        self._collecting_system_metrics = False

        # Configura Redis para persistência de métricas
        self.redis = None
        redis_config = config.get("redis", {})
        if redis_config.get("enabled", False):
            try:
                self.redis = redis.Redis(
                    host=redis_config.get("host", "localhost"),
                    port=redis_config.get("port", 6379),
                    db=redis_config.get("db", 2),  # DB separado para métricas
                    decode_responses=True,
                    socket_timeout=2,
                )
                self.redis.ping()
                logger.info("✅ Conexão com Redis estabelecida para métricas")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao conectar ao Redis para métricas: {str(e)}")

        # Configurações de coleta
        self.gc_interval = config.get("performance", {}).get("memory_management", {}).get("gc_interval", 300)
        self.enable_system_metrics = config.get("monitoring", {}).get("enable_system_metrics", True)

        logger.info("✅ MetricsCollector inicializado com sucesso")

    def record_agent_metrics(self, agent_id: str, metrics: dict[str, any]):
        """
        Registra métricas para um agente específico

        Args:
            agent_id: ID do agente
            metrics: Dicionário com métricas do agente
        """
        timestamp = datetime.utcnow().isoformat()
        key = f"metrics:{agent_id}:{timestamp}"

        # Adiciona timestamp às métricas
        metrics_with_timestamp = {"timestamp": timestamp, **metrics}

        # Armazena no Redis
        if self.redis:
            try:
                self.redis.hset(key, mapping={k: str(v) for k, v in metrics_with_timestamp.items()})
                # Define TTL para 24 horas
                self.redis.expire(key, 86400)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao armazenar métricas no Redis: {str(e)}")

        # Mantém histórico em memória
        if agent_id not in self.metrics_history:
            self.metrics_history[agent_id] = []

        self.metrics_history[agent_id].append(metrics_with_timestamp)

        # Mantém apenas as últimas 1000 métricas por agente para evitar crescimento excessivo
        if len(self.metrics_history[agent_id]) > 1000:
            self.metrics_history[agent_id] = self.metrics_history[agent_id][-1000:]

        # Detecta anomalias
        self._detect_anomalies(agent_id)

        # Coleta métricas de sistema se configurado
        if self.enable_system_metrics and not self._collecting_system_metrics:
            self._collect_system_metrics()

    def _detect_anomalies(self, agent_id: str):
        """
        Detecta anomalias nas métricas de um agente
        """
        if len(self.metrics_history[agent_id]) < 10:
            return

        # Extrai métricas recentes
        recent_metrics = self.metrics_history[agent_id][-10:]

        # Verifica taxa de sucesso
        success_rates = [m.get("success_rate", m.get("success", False) * 100) for m in recent_metrics]

        if np.mean(success_rates) < 50 and np.std(success_rates) > 20:
            anomaly_score = 100 - np.mean(success_rates)
            context = {
                "current_phase": recent_metrics[-1].get("current_phase", "unknown"),
                "success_rate": np.mean(success_rates),
            }
            self._alert_anomaly(agent_id, "falling_success_rate", anomaly_score, context)

        # Verifica tempo de resposta
        response_times = [m.get("avg_response_time", m.get("execution_time", 0)) for m in recent_metrics]

        if np.mean(response_times) > 30 and np.std(response_times) > 10:  # 30 segundos
            anomaly_score = min(100, np.mean(response_times) * 3)
            context = {
                "current_phase": recent_metrics[-1].get("current_phase", "unknown"),
                "avg_response_time": np.mean(response_times),
            }
            self._alert_anomaly(agent_id, "increasing_response_time", anomaly_score, context)

        # Verifica falhas consecutivas
        consecutive_failures = 0
        for metric in reversed(recent_metrics):
            if not metric.get("success", metric.get("success_rate", 100) < 50):
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= 3:
            anomaly_score = consecutive_failures * 30
            context = {
                "consecutive_failures": consecutive_failures,
                "current_phase": recent_metrics[-1].get("current_phase", "unknown"),
                "retry_attempts": recent_metrics[-1].get("retry_attempts", 0),
                "error": recent_metrics[-1].get("error"),
            }
            self._alert_anomaly(agent_id, "consecutive_failures", anomaly_score, context)

    def _alert_anomaly(self, agent_id: str, anomaly_type: str, score: float, context: dict[str, any] = None):
        """
        Cria alerta de anomalia com contexto detalhado
        """
        import traceback

        context = context or {}
        recent_metrics = self.metrics_history.get(agent_id, [])
        last_metric = recent_metrics[-1] if recent_metrics else {}

        consecutive_failures = 0
        for metric in reversed(recent_metrics[-10:]):
            if not metric.get("success", metric.get("success_rate", 100) < 50):
                consecutive_failures += 1
            else:
                break

        stack_trace = None
        try:
            stack_trace = "".join(traceback.format_stack()[-5:-1])
        except Exception:
            pass

        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "anomaly_type": anomaly_type,
            "anomaly_score": score,
            "severity": self._determine_severity(score),
            "consecutive_failures": consecutive_failures,
            "retry_attempts": context.get("retry_attempts", last_metric.get("retry_attempts", 0)),
            "current_phase": context.get("current_phase", last_metric.get("current_phase", "unknown")),
            "last_error": context.get("error", last_metric.get("error")),
            "execution_time": last_metric.get("execution_time", last_metric.get("avg_response_time", 0)),
            "stack_trace": stack_trace,
            "details": (
                f"Anomalia detectada no agente {agent_id}: {anomaly_type} com score {score:.2f}. "
                f"Falhas consecutivas: {consecutive_failures}, "
                f"Fase atual: {context.get('current_phase', 'unknown')}, "
                f"Tentativas: {context.get('retry_attempts', 0)}"
            ),
        }

        self.alerts.append(alert)
        logger.warning(
            f"⚠️ {alert['details']}",
            extra={
                "agent_id": agent_id,
                "anomaly_type": anomaly_type,
                "score": score,
                "consecutive_failures": consecutive_failures,
                "current_phase": context.get("current_phase", "unknown"),
            },
        )

        if alert["severity"] in ["critical", "high"]:
            self._notify_critical_anomaly(alert)

    def _determine_severity(self, score: float) -> str:
        """
        Determina severidade da anomalia baseado no score
        """
        if score >= 90:
            return "critical"
        elif score >= 70:
            return "high"
        elif score >= 50:
            return "medium"
        elif score >= 30:
            return "low"
        else:
            return "info"

    def _notify_critical_anomaly(self, alert: dict[str, any]):
        """
        Notifica sobre anomalia crítica com contexto completo
        """
        logger.critical(
            f"🚨 ANOMALIA CRÍTICA [{alert['severity']}]: {alert['details']}\n"
            f"   Agent: {alert['agent_id']}, Tipo: {alert['anomaly_type']}, Score: {alert['anomaly_score']:.2f}\n"
            f"   Falhas consecutivas: {alert.get('consecutive_failures', 0)}, "
            f"Fase: {alert.get('current_phase', 'unknown')}, "
            f"Tentativas: {alert.get('retry_attempts', 0)}\n"
            f"   Erro: {alert.get('last_error', 'N/A')}\n"
            f"   Timestamp: {alert['timestamp']}"
        )
        if alert.get("stack_trace"):
            logger.debug(f"Stack trace: {alert['stack_trace']}")

    def _collect_system_metrics(self):
        """
        Coleta métricas de sistema
        """
        self._collecting_system_metrics = True
        try:
            # Métricas de CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_cores = psutil.cpu_count()

            # Métricas de memória
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB

            # Métricas de disco
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Tempo de atividade
            uptime = datetime.utcnow() - self.start_time

            system_metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "cpu_cores": cpu_cores,
                "memory_percent": memory_percent,
                "memory_used_gb": memory_used,
                "disk_percent": disk_percent,
                "uptime_seconds": uptime.total_seconds(),
                "process_count": len(psutil.pids()),
                "thread_count": psutil.Process().num_threads(),
            }

            # Registra métricas do sistema
            self.record_agent_metrics("system", system_metrics)

            # Verifica condições críticas
            if memory_percent > 90:
                self.record_alert("high_memory_usage", {"percent": memory_percent})

            if cpu_percent > 95:
                self.record_alert("high_cpu_usage", {"percent": cpu_percent})

            if disk_percent > 90:
                self.record_alert("high_disk_usage", {"percent": disk_percent})

        except Exception as e:
            logger.error(f"Erro ao coletar métricas de sistema: {str(e)}")
        finally:
            self._collecting_system_metrics = False

    def record_alert(self, alert_type: str, details: dict[str, any]):
        """
        Registra um alerta

        Args:
            alert_type: Tipo de alerta
            details: Detalhes do alerta
        """
        # Limpa alertas antigos periodicamente
        self._cleanup_old_alerts()

        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": alert_type,
            "details": details,
            "severity": self._determine_alert_severity(alert_type, details),
        }

        self.alerts.append(alert)

        # Limita tamanho da lista de alertas
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts :]

        log_level = logging.CRITICAL if alert["severity"] == "critical" else logging.WARNING
        logger.log(
            log_level,
            f"🚨 ALERTA [{alert['severity']}]: {alert_type} - {json.dumps(details)}",
        )

        # Armazena alerta no Redis
        if self.redis:
            try:
                alert_key = f"alert:{alert_type}:{alert['timestamp']}"
                self.redis.setex(alert_key, 86400, json.dumps(alert))  # 24 horas
            except Exception as e:
                logger.warning(f"⚠️ Falha ao armazenar alerta no Redis: {str(e)}")

    def _cleanup_old_alerts(self):
        """Remove alertas com mais de 7 dias"""
        current_time = datetime.utcnow()
        if (current_time - self.last_alerts_cleanup).total_seconds() < 3600:  # A cada hora
            return

        self.last_alerts_cleanup = current_time
        cutoff_time = current_time - timedelta(days=7)

        initial_count = len(self.alerts)
        self.alerts = [alert for alert in self.alerts if datetime.fromisoformat(alert["timestamp"]) > cutoff_time]

        removed_count = initial_count - len(self.alerts)
        if removed_count > 0:
            logger.info(f"Cleanup de alertas: removidos {removed_count} alertas antigos")

    def _determine_alert_severity(self, alert_type: str, details: dict[str, any]) -> str:
        """
        Determina severidade do alerta baseado no tipo e detalhes
        """
        critical_alerts = [
            "system_crash",
            "security_breach",
            "data_loss",
            "human_intervention_required",
        ]
        high_alerts = [
            "high_memory_usage",
            "high_cpu_usage",
            "high_disk_usage",
            "service_unavailable",
        ]

        if alert_type in critical_alerts:
            return "critical"
        elif alert_type in high_alerts:
            return "high"
        elif "failure" in alert_type.lower() or "error" in alert_type.lower():
            return "medium"
        else:
            return "low"

    def record_system_error(self, error_message: str, context: dict[str, any] = None):
        """
        Registra erro de sistema

        Args:
            error_message: Mensagem de erro
            context: Contexto adicional
        """
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message,
            "context": context or {},
            "stack_trace": None,  # Em implementação real, capturaria stack trace
        }

        self.record_alert("system_error", error_record)

        # Armazena erro no Redis
        if self.redis:
            try:
                error_key = f"error:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                self.redis.setex(error_key, 604800, json.dumps(error_record))  # 7 dias
            except Exception as e:
                logger.warning(f"⚠️ Falha ao armazenar erro no Redis: {str(e)}")

    def get_agent_performance(self, agent_id: str, hours: int = 24) -> dict[str, any]:
        """
        Retorna métricas de performance de um agente

        Args:
            agent_id: ID do agente
            hours: Número de horas para análise

        Returns:
            Dicionário com métricas de performance
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        if agent_id not in self.metrics_history:
            return {
                "agent_id": agent_id,
                "period_hours": hours,
                "data_points": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "error_rate": 100,
                "recent_errors": [],
            }

        # Filtra métricas pelo período
        relevant_metrics = [
            m for m in self.metrics_history[agent_id] if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]

        if not relevant_metrics:
            return {
                "agent_id": agent_id,
                "period_hours": hours,
                "data_points": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "error_rate": 100,
                "recent_errors": [],
            }

        # Calcula métricas agregadas
        success_count = sum(1 for m in relevant_metrics if m.get("success", m.get("success_rate", 0) > 50))
        total_count = len(relevant_metrics)
        response_times = [m.get("avg_response_time", m.get("execution_time", 0)) for m in relevant_metrics]

        # Coleta erros recentes
        recent_errors = [
            m
            for m in relevant_metrics[-10:]  # Últimas 10 métricas
            if not m.get("success", m.get("success_rate", 0) > 50)
        ]

        return {
            "agent_id": agent_id,
            "period_hours": hours,
            "data_points": total_count,
            "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "error_rate": ((total_count - success_count) / total_count * 100) if total_count > 0 else 100,
            "recent_errors": recent_errors[:5],  # Máximo 5 erros recentes
            "metrics_trend": self._calculate_metrics_trend(relevant_metrics),
        }

    def _calculate_metrics_trend(self, metrics: list[dict[str, any]]) -> dict[str, any]:
        """
        Calcula tendência das métricas (melhorando, estável, piorando)
        """
        if len(metrics) < 2:
            return {"trend": "insufficient_data"}

        # Separa métricas em duas metades
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        # Calcula taxa de sucesso em cada metade
        first_success = sum(1 for m in first_half if m.get("success", m.get("success_rate", 0) > 50)) / len(first_half)
        second_success = sum(1 for m in second_half if m.get("success", m.get("success_rate", 0) > 50)) / len(
            second_half
        )

        # Determina tendência
        if second_success > first_success + 0.1:  # 10% de melhoria
            trend = "improving"
        elif second_success < first_success - 0.1:  # 10% de piora
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "first_period_success_rate": first_success * 100,
            "second_period_success_rate": second_success * 100,
            "change_percent": (second_success - first_success) * 100,
        }

    def get_system_health(self) -> dict[str, any]:
        """
        Retorna saúde geral do sistema
        """
        try:
            # Coleta métricas atuais
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Calcula saúde dos agentes
            agent_health = {}
            for agent_id in self.metrics_history:
                perf = self.get_agent_performance(agent_id, 1)  # Última hora
                agent_health[agent_id] = {
                    "success_rate": perf["success_rate"],
                    "avg_response_time": perf["avg_response_time"],
                    "status": "healthy"
                    if perf["success_rate"] >= 80
                    else "degraded"
                    if perf["success_rate"] >= 50
                    else "unhealthy",
                }

            # Determina status geral
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                overall_status = "critical"
            elif any(status["status"] == "unhealthy" for status in agent_health.values()):
                overall_status = "degraded"
            elif any(status["status"] == "degraded" for status in agent_health.values()):
                overall_status = "warning"
            else:
                overall_status = "healthy"

            # Contagem de alertas recentes (última hora)
            recent_alerts = [
                alert
                for alert in self.alerts
                if datetime.fromisoformat(alert["timestamp"]) > datetime.utcnow() - timedelta(hours=1)
            ]

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": overall_status,
                "system_metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                },
                "agent_health": agent_health,
                "recent_alerts_count": len(recent_alerts),
                "active_anomalies": len([a for a in self.alerts if a.get("anomaly_score", 0) > 50]),
                "alerts_summary": self._summarize_alerts(recent_alerts),
            }

        except Exception as e:
            logger.error(f"Erro ao obter saúde do sistema: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "unknown",
                "error": str(e),
            }

    def _summarize_alerts(self, alerts: list[dict[str, any]]) -> dict[str, any]:
        """
        Sumariza alertas recentes
        """
        if not alerts:
            return {"count": 0}

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        type_counts = {}

        for alert in alerts:
            severity = alert.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            alert_type = alert.get("alert_type", "unknown")
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

        # Encontra alerta mais crítico
        critical_severities = ["critical", "high", "medium"]
        most_critical = next((s for s in critical_severities if severity_counts.get(s, 0) > 0), "low")

        return {
            "count": len(alerts),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "most_critical_severity": most_critical,
        }

    def get_performance_report(self, hours: int = 24) -> dict[str, any]:
        """
        Gera relatório de performance completo

        Args:
            hours: Número de horas para o relatório

        Returns:
            Dicionário com relatório de performance
        """
        report_time = datetime.utcnow()
        cutoff_time = report_time - timedelta(hours=hours)

        # Saúde do sistema
        system_health = self.get_system_health()

        # Performance de todos os agentes
        agent_performance = {}
        for agent_id in self.metrics_history:
            perf = self.get_agent_performance(agent_id, hours)
            agent_performance[agent_id] = perf

        # Alertas recentes
        recent_alerts = [alert for alert in self.alerts if datetime.fromisoformat(alert["timestamp"]) > cutoff_time]

        # Calcula estatísticas gerais
        total_operations = sum(perf["data_points"] for perf in agent_performance.values())
        successful_operations = sum(
            (perf["success_rate"] / 100) * perf["data_points"] for perf in agent_performance.values()
        )
        avg_response_time = (
            np.mean([perf["avg_response_time"] for perf in agent_performance.values() if perf["data_points"] > 0])
            if agent_performance
            else 0
        )

        return {
            "report_generated_at": report_time.isoformat(),
            "period_hours": hours,
            "period_start": cutoff_time.isoformat(),
            "system_health": system_health,
            "agent_performance": agent_performance,
            "summary_statistics": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                "average_response_time": avg_response_time,
                "total_alerts": len(recent_alerts),
                "critical_alerts": len([a for a in recent_alerts if a.get("severity") == "critical"]),
            },
            "recommendations": self._generate_performance_recommendations(system_health, agent_performance),
        }

    def _generate_performance_recommendations(
        self, system_health: dict[str, any], agent_performance: dict[str, any]
    ) -> list[str]:
        """
        Gera recomendações baseadas na performance do sistema
        """
        recommendations = []

        # Recomendações baseadas na saúde do sistema
        system_metrics = system_health.get("system_metrics", {})
        if system_metrics.get("cpu_percent", 0) > 80:
            recommendations.append("Considerar escalonamento horizontal ou otimização de código CPU-bound")

        if system_metrics.get("memory_percent", 0) > 80:
            recommendations.append("Implementar limpeza de cache mais agressiva e otimizar uso de memória")

        if system_metrics.get("disk_percent", 0) > 80:
            recommendations.append("Limpar arquivos temporários e considerar expansão de armazenamento")

        # Recomendações baseadas na performance dos agentes
        for agent_id, perf in agent_performance.items():
            if perf["success_rate"] < 70:
                recommendations.append(
                    f"Revisar prompts e parâmetros do {agent_id} - taxa de sucesso baixa ({perf['success_rate']:.1f}%)"
                )

            if perf["avg_response_time"] > 30:  # 30 segundos
                recommendations.append(
                    f"Otimizar LLM calls para {agent_id} - tempo de resposta alto ({perf['avg_response_time']:.1f}s)"
                )

        # Recomendações gerais
        if not recommendations:
            recommendations.append("Sistema operando dentro dos parâmetros normais")

        return recommendations[:10]  # Limita a 10
