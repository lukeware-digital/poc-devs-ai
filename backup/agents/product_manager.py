import json
import logging

from agents.base_agent import BaseAgent
from utils.markdown_parser import extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent2_ProductManager(BaseAgent):
    """Agent-2: Product Manager - Gera histórias de usuário"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
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

        Formato de resposta Markdown:

        ## User Stories

        ### US-1
        **Description:** Como [persona específica], eu quero [ação clara] para [benefício mensurável]
        **Priority:** high
        **Estimated Story Points:** 5

        **Acceptance Criteria:**
        - Critério testável 1 em formato de string
        - Critério testável 2 em formato de string
        - Critério testável 3 em formato de string

        **Definition of Done:**
        - Código implementado e revisado
        - Testes unitários com cobertura > 80%
        - Documentação atualizada
        - Code review aprovado
        - Funcionalidade testada manualmente

        ---

        ## Product Backlog
        - ID da história prioritária para próxima sprint

        ## Release Planning

        ### MVP Scope
        - IDs das histórias essenciais para MVP

        ### Future Enhancements
        - IDs das histórias para versões futuras

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
            user_stories = extract_structured_data_from_markdown(response)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(self.agent_id, "technical", "user_stories", user_stories, 0.9)

            # Lê arquivo do agente anterior
            previous_content = self._read_previous_agent_md(2)

            # Gera nova seção de histórias de usuário
            new_section = "# HISTÓRIAS DE USUÁRIO\n\n"
            for story in user_stories.get("user_stories", []):
                story_id = story.get("id", "N/A")
                description = story.get("description", "N/A")
                priority = story.get("priority", "N/A")
                story_points = story.get("estimated_story_points", 0)

                new_section += f"### {story_id}\n\n"
                new_section += f"**{description}**\n\n"
                new_section += f"**Prioridade:** {priority}\n"
                new_section += f"**Story Points:** {story_points}\n\n"
                new_section += "**Critérios de Aceitação:**\n\n"
                for criterion in story.get("acceptance_criteria", []):
                    new_section += f"- [ ] {criterion}\n"
                new_section += "\n**Definition of Done:**\n\n"
                for item in story.get("definition_of_done", []):
                    new_section += f"- [ ] {item}\n"
                new_section += "\n---\n\n"

            if user_stories.get("product_backlog"):
                new_section += "## Product Backlog\n\n"
                for story_id in user_stories.get("product_backlog", []):
                    new_section += f"- {story_id}\n"
                new_section += "\n"

            if user_stories.get("release_planning"):
                release_planning = user_stories.get("release_planning", {})
                new_section += "## Release Planning\n\n"
                if release_planning.get("mvp_scope"):
                    new_section += "### MVP Scope\n\n"
                    for story_id in release_planning.get("mvp_scope", []):
                        new_section += f"- {story_id}\n"
                    new_section += "\n"
                if release_planning.get("future_enhancements"):
                    new_section += "### Future Enhancements\n\n"
                    for story_id in release_planning.get("future_enhancements", []):
                        new_section += f"- {story_id}\n"
                    new_section += "\n"

            md_content = self._build_accumulative_md(
                previous_content, new_section, "HISTÓRIAS DE USUÁRIO", 2, "Agent 1"
            )
            await self._save_markdown_file("agent2_historias.md", md_content)

            return {"status": "success", "user_stories": user_stories}
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Product Manager: {str(e)}")
            raise
