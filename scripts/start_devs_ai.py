#!/usr/bin/env python3
"""
Script de inicialização do DEVs AI
"""
import asyncio
import logging
import sys
import subprocess
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from __init__ import DEVsAISystem

async def start_system():
    """Inicializa o sistema DEVs AI"""
    print("""
    🚀 DEVs AI - Sistema Multiagente de Desenvolvimento
    ==================================================
    """)
    
    # Verifica dependências
    if not check_dependencies():
        print("❌ Dependências não atendidas. Verifique o setup.")
        return
        
    try:
        # Inicializa sistema
        system = DEVsAISystem()
        await system.initialize()
        print("✅ Sistema inicializado com sucesso!")
        
        # Mostra status
        status = system.get_system_status()
        print(f"📊 Status dos Serviços:")
        for service, status_value in status['services'].items():
            print(f"   - {service}: {status_value}")
            
        print(f"\n🤖 Agentes Disponíveis: {', '.join(status['agents_ready'])}")
        
        # Mantém o sistema rodando
        print("\n"
              "🔄 Sistema em execução. Digite 'exit' para parar ou descreva seu projeto abaixo.")
        print("=" * 60)
        
        while True:
            user_input = input("\n💻 Sua solicitação: ")
            if user_input.lower() in ['exit', 'quit', 'sair']:
                break
                
            print("\n🧠 Processando sua solicitação...")
            result = await system.process_request(user_input)
            
            if result['success']:
                print("\n✅ Projeto concluído com sucesso!")
                if 'final_delivery' in result.get('final_state', {}):
                    print("📦 Entrega final preparada!")
                    print(f"📊 Métricas de qualidade: {result['final_state']['final_delivery'].get('quality_metrics', {})}")
            else:
                print(f"\n❌ Erro no processamento: {result.get('error')}")
                if 'recovery_suggestions' in result:
                    print("💡 Sugestões para recuperação:")
                    for suggestion in result['recovery_suggestions']:
                        print(f"   - {suggestion}")
                        
    except KeyboardInterrupt:
        print("\n\n🛑 Parando sistema...")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logging.exception("Erro não tratado")
        sys.exit(1)
        
def check_dependencies() -> bool:
    """Verifica se todas as dependências estão disponíveis"""
    dependencies_ok = True
    
    print("🔍 Verificando dependências...")
    
    # Verifica Python
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Verifica bibliotecas Python
    try:
        import redis
        print("✅ Redis client")
    except ImportError:
        print("❌ Redis client não encontrado. Instale com: pip install redis")
        dependencies_ok = False
        
    try:
        import chromadb
        print("✅ ChromaDB client")
    except ImportError:
        print("❌ ChromaDB client não encontrado. Instale com: pip install chromadb")
        dependencies_ok = False
        
    try:
        import aiohttp
        print("✅ aiohttp")
    except ImportError:
        print("❌ aiohttp não encontrado. Instale com: pip install aiohttp")
        dependencies_ok = False
        
    try:
        import numpy
        print("✅ NumPy")
    except ImportError:
        print("❌ NumPy não encontrado. Instale com: pip install numpy")
        dependencies_ok = False
        
    try:
        from pydantic import BaseModel
        print("✅ Pydantic")
    except ImportError:
        print("❌ Pydantic não encontrado. Instale com: pip install pydantic")
        dependencies_ok = False
        
    # Verifica serviços externos
    print("\n🔌 Verificando serviços externos...")
    
    # Verifica Docker
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("✅ Docker")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Docker não encontrado ou não está em execução")
        
    # Verifica Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_timeout=2)
        r.ping()
        print("✅ Redis server")
    except:
        print("⚠️  Redis server não encontrado ou não está em execução")
        
    # Verifica ChromaDB
    try:
        import chromadb
        client = chromadb.HttpClient(host='localhost', port=8000)
        client.heartbeat()
        print("✅ ChromaDB server")
    except:
        print("⚠️  ChromaDB server não encontrado ou não está em execução")
        
    # Verifica Ollama
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            print("✅ Ollama server")
        else:
            print("⚠️  Ollama server não está respondendo corretamente")
    except:
        print("⚠️  Ollama server não encontrado ou não está em execução")
        
    return dependencies_ok

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_system())