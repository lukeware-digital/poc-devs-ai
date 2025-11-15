import json
import logging

from agents.base_agent import BaseAgent
from utils.json_parser import extract_json_from_response

logger = logging.getLogger("devs-ai")


class Agent2_ProductManager(BaseAgent):
    """Agent-2: Product Manager - Gera histórias de usuário"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        specification = task["specification"]

        # Carrega template especializado
        template_base = self._build_prompt("product_manager", {})

        prompt = f"""
        {template_base}

        Crie histórias de usuário baseado na especificação:
        ESPECIFICAÇÃO: {json.dumps(specification, indent=2)}

        DIRETRIZES INVEST (cada história deve ser):
        - Independent: Pode ser desenvolvida independentemente de outras
        - Negotiable: Detalhes podem ser negociados sem alterar a essência
        - Valuable: Entrega valor de negócio mensurável
        - Estimable: Pode ser estimada com precisão razoável
        - Small: Pequena o suficiente para ser completada em uma sprint
        - Testable: Pode ser testada e validada objetivamente

        REGRAS PARA HISTÓRIAS DE USUÁRIO:
        1. Formato: "Como [persona específica], eu quero [ação clara e específica] para [benefício mensurável]"
        2. Evite duplicatas - cada história deve ser única e distinta
        3. Seja específico - evite descrições genéricas como "gerenciar tarefas"
        4. Identifique personas reais (ex: "Como desenvolvedor", "Como administrador", "Como usuário final")

        CRITÉRIOS DE ACEITAÇÃO:
        - Devem ser strings de texto descritivas e testáveis
        - Cada critério deve ser verificável e mensurável
        - Mínimo de 3 critérios por história
        - Formato: strings simples, NÃO objetos ou dicionários
        - Exemplo CORRETO: "O endpoint POST /tasks retorna status 201 quando uma tarefa é criada"
        - Exemplo INCORRETO: {{"criteria_id": 0}} ou qualquer formato de objeto

        PRIORIZAÇÃO:
        - "high": Funcionalidade crítica para MVP, bloqueia outras features, alto valor de negócio
        - "medium": Importante mas não bloqueante, valor moderado
        - "low": Melhorias, nice-to-have, baixo impacto imediato
        - Varie as prioridades baseado em: valor de negócio, dependências técnicas, complexidade, impacto no usuário

        STORY POINTS (escala Fibonacci):
        - Use apenas: 1, 2, 3, 5, 8, 13
        - 1-2: Tarefas muito simples, mudanças pequenas
        - 3-5: Tarefas moderadas, algumas horas de trabalho
        - 8: Tarefas complexas, requerem planejamento
        - 13: Tarefas muito complexas, podem precisar ser quebradas
        - Varie os pontos baseado em complexidade real, não use sempre o mesmo valor

        DEFINITION OF DONE (obrigatório para cada história):
        - Código implementado e revisado
        - Testes unitários escritos e passando (cobertura mínima 80%)
        - Testes de integração quando aplicável
        - Documentação atualizada (README, comentários, API docs)
        - Code review aprovado
        - Sem erros de linting ou warnings críticos
        - Funcionalidade testada manualmente
        - Deploy em ambiente de desenvolvimento validado
        - Adicione itens específicos relacionados à história quando necessário

        VALIDAÇÃO:
        - Revise todas as histórias para garantir que não há duplicatas
        - Certifique-se de que cada história é específica e única
        - Verifique que todos os campos estão preenchidos corretamente
        - Garanta que acceptance_criteria são strings, não objetos

        Formato de resposta JSON:
        {{
            "user_stories": [
                {{
                    "id": "US-1",
                    "description": "Como [persona específica], eu quero [ação clara] para [benefício mensurável]",
                    "acceptance_criteria": [
                        "Critério testável 1 em formato de string",
                        "Critério testável 2 em formato de string",
                        "Critério testável 3 em formato de string"
                    ],
                    "priority": "high",
                    "definition_of_done": [
                        "Código implementado e revisado",
                        "Testes unitários com cobertura > 80%",
                        "Documentação atualizada",
                        "Code review aprovado",
                        "Funcionalidade testada manualmente"
                    ],
                    "estimated_story_points": 5
                }}
            ],
            "product_backlog": [
                "ID da história prioritária para próxima sprint"
            ],
            "release_planning": {{
                "mvp_scope": [
                    "IDs das histórias essenciais para MVP"
                ],
                "future_enhancements": [
                    "IDs das histórias para versões futuras"
                ]
            }}
        }}

        IMPORTANTE: 
        - acceptance_criteria deve ser array de STRINGS, nunca objetos ou dicionários
        - definition_of_done deve ser array de STRINGS com itens específicos
        - Varie prioridades e story points baseado em análise real
        - Evite duplicatas e histórias genéricas
        """

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent2", {}).get("temperature", 0.8)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            user_stories = extract_json_from_response(response)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(self.agent_id, "technical", "user_stories", user_stories, 0.9)

            # Salva user_stories.md
            md_content = "# User Stories\n\n"
            for story in user_stories.get("user_stories", []):
                md_content += f"## {story.get('id', 'N/A')}\n\n"
                md_content += f"**Description:** {story.get('description', 'N/A')}\n\n"
                md_content += f"**Priority:** {story.get('priority', 'N/A')}\n\n"
                md_content += f"**Story Points:** {story.get('estimated_story_points', 0)}\n\n"
                md_content += "**Acceptance Criteria:**\n"
                for criterion in story.get("acceptance_criteria", []):
                    md_content += f"- {criterion}\n"
                md_content += "\n**Definition of Done:**\n"
                for item in story.get("definition_of_done", []):
                    md_content += f"- {item}\n"
                md_content += "\n---\n\n"
            await self._save_markdown_file("user_stories.md", md_content)

            return {"status": "success", "user_stories": user_stories}
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Product Manager: {str(e)}")
            raise
