# README.md — DEVs AI

# 🧠 DEVs AI

**Plataforma Multiagente para Automação Completa do Desenvolvimento de Software**

O **DEVs AI** é um sistema multiagente avançado que automatiza todo o ciclo de desenvolvimento de software utilizando modelos de linguagem **open-source**, rodando localmente, com arquitetura modular, segura e escalável. Cada agente representa um papel real em uma equipe de engenharia: analista, product manager, arquiteto, tech lead, scaffolder, desenvolvedor, revisor e finalizador.

O sistema foi projetado para ser **100% local**, suportar **execução offline**, e operar com **LLMs via Ollama, HuggingFace ou LLMStudio**, sempre com **guardrails rigorosos**, validação Pydantic, RAG especializado, sandboxing duplo e orquestração via **LangGraph**.

---

## 🚀 Objetivo do Projeto

Transformar instruções naturais fornecidas pelo usuário em **projetos completos de software**, gerando:

* Especificação formal
* Histórias e épicos
* Arquitetura
* Tarefas técnicas
* Código gerado automaticamente
* Testes
* Revisões
* Documentação
* Releases

Tudo isso com fluxos auditáveis, recuperação de falhas e possibilidade de supervisão humana.

---

## ⚙️ Arquitetura Geral

O DEVs AI é composto por:

* **Agentes Autônomos** — Cada um com função específica no pipeline
* **Orquestrador LangGraph** — Controla o fluxo, loops, recovery e estado
* **RAG Avançado** — Para contexto técnico profundo e consultas em múltiplas bases
* **LLMs Locais** — Modelos open-source especializados por agente
* **Guardrails** — Segurança, isolamento, tokens de capacidade e validação
* **Sistema de Contexto Compartilhado** — Estado global versionado entre agentes
* **Mecanismo de Recuperação de Falhas** — Circuit breakers, fallback agents, rollback
* **Painel de Supervisão Humana** (V1.1) — Monitoramento e intervenção

---

## 🧩 Principais Tecnologias

* **Python 3.10+**
* **LangGraph** para orquestração multiagente
* **Ollama / LLMStudio / HuggingFace** para modelos locais
* **ChromaDB** + VectorDB para RAG
* **PostgreSQL** para metadados e persistência
* **Redis Streams** para cache e mensageria
* **PydanticAI** para validação formal
* **Docker + Sandbox Duplo**
* **Painel web (supervisão)** via API + interface frontend

---

## 🤖 Agentes do Sistema (V1.1 Completo)

### Agent-1 — Analista de Requisitos

Transforma linguagem natural em uma **spec.json** validada.

### Agent-2 — Product Manager

Gera épicos, histórias, critérios de aceite.

### Agent-3 — Arquiteto (V1.1)

Define arquitetura, diagramas, protocolos, decisões não funcionais.

### Agent-4 — Tech Lead

Gera tasks técnicas, define stack, padrões e dependências.

### Agent-5 — Scaffolder

Cria a estrutura inicial do repositório.

### Agent-6 — Desenvolvedor

Gera código, testes, módulos e abre PRs.

### Agent-7 — Code Reviewer

Aponta problemas, melhorias, segurança e padrões.

### Agent-8 — Refatorador e Finalizador

Aplica correções, refatorações, escreve documentação e release notes.

### Fallback Agents (V1.1)

Agentes especializados em recuperação quando ocorre falha crítica.

---

## 🔄 Fluxo Completo (LangGraph)

```
User
  ↓
Agent-1 → Agent-2 → Agent-3 → Agent-4 → Agent-5 → Agent-6 → Agent-7 → Agent-8 → User
  ↑            ↑             ↑            ↑            ↑            ↑
  └────────────┴─────────────┴────────────┴────────────┴────────────┘
               Recovery System + Human Supervisor
```

O sistema possui:

* Circuit breakers automáticos
* Rollback versionado
* Reexecução através de fallback agents
* Solicitação de aprovação humana para operações críticas

---

## 📚 RAG — Retrieval-Augmented Generation

### Funções principais:

* Recuperar contexto histórico
* Suportar decisões técnicas
* Indexar código, commits, arquitetura, specs e histórias
* Utilizar modelos de embedding especializados (código + linguagem natural)
* Realizar reranking contextual

O RAG possui pipelines independentes para:

* documentos
* histórias
* código
* padrões arquiteturais
* commits

---

## 🔐 Segurança e Guardrails

O DEVs AI possui camadas rígidas de proteção:

* **Execução 100% local**
* **Sem acesso à internet**
* **Sandbox duplo** (Docker + executor controlado)
* **Capability Tokens** para operações sensíveis (git, schema, etc.)
* **Validação Pydantic estrita**
* **Auditoria completa de logs**
* **Isolamento de rede**
* **Supervisão humana obrigatória em operações de alto impacto**

---

## 📁 Estrutura do Repositório

```
/devs-ai
 ├── agents/
 │    ├── agent1/
 │    ├── agent2/
 │    ├── agent3/
 │    ├── agent4/
 │    ├── agent5/
 │    ├── agent6/
 │    ├── agent7/
 │    ├── agent8/
 │    └── fallback/
 ├── orchestrator/
 │    ├── langgraph_flow.py
 │    ├── recovery_system.py
 │    └── state_manager.py
 ├── shared_context/
 ├── supervision/
 │    ├── web_dashboard/
 │    └── api_endpoints.py
 ├── rag/
 │    ├── indexers/
 │    ├── retrievers/
 │    └── rerankers/
 ├── db/
 ├── guardrails/
 ├── monitoring/
 ├── schemas/
 ├── prompts/
 ├── models/
 ├── tests/
 ├── docs/
 ├── diagrams/
 ├── scripts/
 ├── config/
 ├── docker-compose.yml
 ├── requirements.txt
 ├── .env.example
 ├── SECURITY.md
 └── README.md
```

---

## 🖥️ Requisitos de Hardware

### Mínimo para V1.0

* 8 cores CPU
* 32GB RAM
* GPU 8GB VRAM (Llama/Mistral quantizados)
* SSD 100GB

### Uso ideal (com Agent-3 e RAG avançado)

* 16+ cores
* 64GB RAM
* GPU 16–24GB VRAM
* SSD NVMe 1TB

---

## 🧪 Testes

A suíte de testes é dividida em:

* Unit
* Integration
* Failure scenarios (V1.1)
* RAG validation
* Guardrail enforcement

---

## 🛡️ Critérios de Sucesso

* JSON sempre válido
* Pipelines sem falhas
* Circuit breakers atuando corretamente
* Código compilável
* Testes automáticos passando
* Qualidade consistente revisada pelo Agent-7
* Recuperação automática < 2 min

---

## 📦 Roadmap

### ✓ Versão 1.0

Base multiagente + RAG inicial + agentes principais.

### ✓ Versão 1.1

Arquitetura completa, fallback agents, contexto compartilhado, painel humano.

### ⏳ Versão 1.2

Fine-tuning, CI/CD local, aprendizado contínuo.

### 🔮 Versão 2.0

Automação completa de deploy, multi-projetos, performance profissional.

---

## 📄 Licença

**MIT License**
Consulte `SECURITY.md` para normas adicionais de segurança.

---

## 🧭 Conclusão

O **DEVs AI** se posiciona como uma plataforma sólida, completa e segura para **automatizar o desenvolvimento de software utilizando IA local**. Ele integra agentes especializados, pipelines formais, tolerância a falhas e supervisão humana — tornando-se uma solução moderna, expansível e prática para equipes e desenvolvedores individuais que desejam elevar sua produtividade ao próximo nível.

Explorar o DEVs AI é abrir caminho para uma nova geração de ferramentas de engenharia assistida por IA.

---