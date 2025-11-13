#!/usr/bin/env python3
"""
Script de inicialização do DEVs AI
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Adiciona o diretório raiz ao path
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))

from devs_ai.main import DEVsAISystem


async def start_system():
    """Inicializa o sistema DEVs AI"""
    _print_banner()

    if not check_dependencies():
        print("❌ Dependências não atendidas. Verifique o setup.")
        return

    try:
        system = await _initialize_system()
        await _run_main_loop(system)
    except KeyboardInterrupt:
        print("\n\n🛑 Parando sistema...")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logging.exception("Erro não tratado")
        sys.exit(1)


def _print_banner():
    """Imprime banner do sistema"""
    print("""
    🚀 DEVs AI - Sistema Multiagente de Desenvolvimento
    ==================================================
    """)


async def _initialize_system():
    """Inicializa o sistema e retorna instância"""
    system = DEVsAISystem()
    await system.initialize()
    print("✅ Sistema inicializado com sucesso!")

    status = system.get_system_status()
    print("📊 Status dos Serviços:")
    for service, status_value in status["services"].items():
        print(f"   - {service}: {status_value}")

    print(f"\n🤖 Agentes Disponíveis: {', '.join(status['agents_ready'])}")
    return system


async def _run_main_loop(system):
    """Executa loop principal de interação"""
    print("\n🔄 Sistema em execução. Digite 'exit' para parar ou descreva seu projeto abaixo.")
    print("=" * 60)

    while True:
        user_input = input("\n💻 Sua solicitação: ")
        if user_input.lower() in ["exit", "quit", "sair"]:
            break

        print("\n🧠 Processando sua solicitação...")
        result = await system.process_request(user_input)
        _print_result(result)


def _print_result(result: dict):
    """Imprime resultado do processamento"""
    if result["success"]:
        print("\n✅ Projeto concluído com sucesso!")
        if "final_delivery" in result.get("final_state", {}):
            print("📦 Entrega final preparada!")
            quality_metrics = result["final_state"]["final_delivery"].get("quality_metrics", {})
            print(f"📊 Métricas de qualidade: {quality_metrics}")
    else:
        print(f"\n❌ Erro no processamento: {result.get('error')}")
        if "recovery_suggestions" in result:
            print("💡 Sugestões para recuperação:")
            for suggestion in result["recovery_suggestions"]:
                print(f"   - {suggestion}")


def check_dependencies() -> bool:
    """Verifica se todas as dependências estão disponíveis"""
    print("🔍 Verificando dependências...")
    print(f"✅ Python {sys.version.split()[0]}")

    python_deps = _check_python_libraries()
    _check_external_services()

    return python_deps


def _check_python_libraries() -> bool:
    """Verifica bibliotecas Python"""
    libs = {
        "redis": "Redis client",
        "chromadb": "ChromaDB client",
        "aiohttp": "aiohttp",
        "numpy": "NumPy",
        "pydantic": "Pydantic",
    }

    all_ok = True
    import importlib.util

    for module, name in libs.items():
        if importlib.util.find_spec(module):
            print(f"✅ {name}")
        else:
            print(f"❌ {name} não encontrado. Instale com: pip install {module}")
            all_ok = False

    return all_ok


def _check_external_services():
    """Verifica serviços externos"""
    print("\n🔌 Verificando serviços externos...")
    _check_docker()
    _check_redis_server()
    _check_chromadb_server()
    _check_ollama_server()


def _check_docker():
    """Verifica Docker"""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        print("✅ Docker")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Docker não encontrado ou não está em execução")


def _check_redis_server():
    """Verifica Redis server"""
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, socket_timeout=2)
        r.ping()
        print("✅ Redis server")
    except Exception:
        print("⚠️  Redis server não encontrado ou não está em execução")


def _check_chromadb_server():
    """Verifica ChromaDB server"""
    try:
        import chromadb

        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        print("✅ ChromaDB server")
    except Exception:
        print("⚠️  ChromaDB server não encontrado ou não está em execução")


def _check_ollama_server():
    """Verifica Ollama server"""
    try:
        import requests

        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama server")
        else:
            print("⚠️  Ollama server não está respondendo corretamente")
    except Exception:
        print("⚠️  Ollama server não encontrado ou não está em execução")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_system())
