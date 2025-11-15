# Exemplos de LangGraph

## Exemplo 1 - Grafo Básico (`exemple_1.py`)

Grafo simples com um único nó que responde perguntas usando LLM.

**Funcionalidades:**
- Recebe uma pergunta do usuário
- Processa através do modelo LLM (gemma3:4b)
- Retorna a resposta
- Gera visualização Mermaid do grafo

**Como testar:**
```bash
python exemples/exemple_1.py
```

**Saída esperada:**
- Resposta do modelo para a pergunta "Quem descobriu a América?"
- Diagrama Mermaid do grafo

---

## Exemplo 1 com Gráfico (`exemple_1_with_graph.py`)

Versão do exemplo 1 que gera uma imagem PNG do grafo.

**Funcionalidades:**
- Mesmas funcionalidades do exemplo 1
- Gera arquivo `graph.png` com visualização do grafo

**Como testar:**
```bash
python exemples/exemple_1_with_graph.py
```

**Saída esperada:**
- Arquivo `graph.png` criado na pasta raiz
- Resposta do modelo para a pergunta "Quem descobriu a América?"

---

## Exemplo 2 - Grafo com Roteamento Condicional (`exemple_2.py`)

Grafo que roteia para diferentes nós baseado no tipo de solicitação: soma, divisão ou resposta direta.

**Funcionalidades:**
- Roteamento condicional baseado em palavras-chave
- Nó de soma: extrai números e realiza soma
- Nó de divisão: extrai dois números e realiza divisão
- Nó de resposta direta: usa LLM para responder perguntas gerais
- Mantém histórico de mensagens no estado

**Como testar:**
```bash
python exemples/exemple_2.py
```

**Casos de teste incluídos:**
- "Quanto é 2+2?" → Roteia para soma
- "Divida 10 por 2" → Roteia para divisão
- "Quem pintou a Mona Lisa?" → Roteia para resposta direta
- "Some 5, 10 e 15" → Roteia para soma

**Saída esperada:**
- Arquivo `graph.png` criado
- Resultados de cada caso de teste

---

## Exemplo 3 - Grafo com Classificação (`exemple_3.py`)

Grafo que classifica a entrada e roteia para cálculo, curiosidade ou erro.

**Funcionalidades:**
- Nó de classificação que identifica o tipo de pergunta
- Nó de cálculo: retorna resposta fixa para cálculos
- Nó de curiosidade: usa LLM para responder perguntas
- Nó de erro: trata perguntas não reconhecidas

**Como testar:**
```bash
python exemples/exemple_3.py
```

**Casos de teste incluídos:**
- "Quanto é 2+2?" → Classificado como cálculo
- "Quem descobriu a América em uma frase?" → Classificado como curiosidade
- "O que é a vida em uma frase?" → Classificado como curiosidade
- "Me diga um comando especial?" → Classificado como erro

**Saída esperada:**
- Arquivo `graph2.png` criado
- Resultados formatados de cada exemplo com pergunta, resposta e tipo

---

## Exemplo 4 - Grafo com Pesquisa (`exemple_4.py`)

Extensão do exemplo 3 que adiciona funcionalidade de pesquisa na web.

**Funcionalidades:**
- Todas as funcionalidades do exemplo 3
- Nó de pesquisa: utiliza DuckDuckGo para pesquisar na web
- Classificação adicional para identificar solicitações de pesquisa

**Como testar:**
```bash
python exemples/exemple_4.py
```

**Casos de teste incluídos:**
- "Pesquise sobre, quanto foi criado o DeepSeek?" → Classificado como pesquisa

**Saída esperada:**
- Arquivo `graph2.png` criado
- Resultado da pesquisa com informações do DuckDuckGo

**Nota:** Requer conexão com internet para funcionar a pesquisa.

---

## Requisitos

- Python 3.x
- Dependências instaladas (ver `requirements.txt` na raiz do projeto)
- Ollama rodando com os modelos: `gemma3:4b` e `llama3.2:3b`
- Para o exemplo 4: conexão com internet

## Estrutura dos Grafos

Todos os exemplos utilizam LangGraph com:
- **StateGraph**: Gerencia o estado compartilhado entre nós
- **GraphState**: Modelo Pydantic que define a estrutura do estado
- **Nodes**: Funções que processam o estado
- **Edges**: Conexões entre nós (condicionais ou diretas)

