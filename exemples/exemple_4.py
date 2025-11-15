from langchain.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

# 2- Definindo o Modelo
llm = ChatOllama(model="llama3.2:3b")


# 3- Definindo o State
class GraphState(BaseModel):
    input: str
    output: str
    tipo: str | None = None


# 4- Função de implementar calculo
def realizar_calculo(state: GraphState) -> GraphState:
    return GraphState(input=state.input, output="Resposta do calculo é: 42")


# 5- Função de implementar conversa
def responder_curiosidade(state: GraphState) -> GraphState:
    response = llm.invoke([HumanMessage(content=state.input)])
    return GraphState(input=state.input, output=response.content)


# 6- Função de implementar pesquisa
def realizar_pesquisa(state: GraphState) -> GraphState:
    wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)
    search = DuckDuckGoSearchRun(api_wrapper=wrapper)
    response = search.run(state.input)
    return GraphState(input=state.input, output=response)


# 6- Função para tratar perguntas não reconhecidas
def responder_erros(state: GraphState) -> GraphState:
    return GraphState(input=state.input, output="Desculpe, não consegui entender a sua pergunta.")


# 7- Função de classificar dos nodes
def classificar(state: GraphState) -> GraphState:
    pergunta = state.input.lower()
    if any(palavra in pergunta for palavra in ["soma", "quanto é", "+", "calcular"]):
        tipo = "calculo"
    elif any(
        palavra in pergunta for palavra in ["quem", "onde", "quando", "por que", "como", "o que", "o quê", "qual"]
    ):
        tipo = "curiosidade"
    elif any(palavra in pergunta for palavra in ["pesquisar", "pesquise", "buscar", "busque", "encontrar", "encontre"]):
        tipo = "pesquisa"
    else:
        tipo = "erro"
    return GraphState(input=state.input, output="", tipo=tipo)


# 8- Construindo o graph
graph = StateGraph(GraphState)
graph.add_node("classificar", classificar)
graph.add_node("realizar_calculo", realizar_calculo)
graph.add_node("responder_curiosidade", responder_curiosidade)
graph.add_node("responder_erros", responder_erros)
graph.add_node("realizar_pesquisa", realizar_pesquisa)

# 9- Definindo ponto de entrada do grafo (onde começa a execução)
graph.set_entry_point("classificar")


# 10- Definindo função de roteamento condicional (decide para onde ir após classificar)
def route_classificar(state: GraphState) -> str:
    if state.tipo == "calculo":
        return "realizar_calculo"
    elif state.tipo == "curiosidade":
        return "responder_curiosidade"
    elif state.tipo == "pesquisa":
        return "realizar_pesquisa"
    elif state.tipo == "erro":
        return "responder_erros"
    else:
        return END


# 11- Adicionando arestas condicionais que SAEM do nó "classificar"
graph.add_conditional_edges(
    "classificar",
    route_classificar,
    {
        "realizar_calculo": "realizar_calculo",
        "responder_curiosidade": "responder_curiosidade",
        "responder_erros": "responder_erros",
        "realizar_pesquisa": "realizar_pesquisa",
    },
)

# 12- Conectando nós finais ao END
graph.add_edge("realizar_calculo", END)
graph.add_edge("responder_curiosidade", END)
graph.add_edge("responder_erros", END)
graph.add_edge("realizar_pesquisa", END)

# 13- Compilando o graph
exported_graph = graph.compile()

png_draw_method = exported_graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
with open("graph2.png", "wb") as f:
    f.write(png_draw_method)
print("Grafo salvo como graph.png")

# 14- Executando o graph
if __name__ == "__main__":
    exemplos = [
        # "Quanto é 2+2?",
        # "Quem descobriu a América em uma frase?",
        # "O que é a vida em uma frase?",
        # "Me diga um comando especial?",
        "Pesquise sobre, quanto foi criado o DeepSeek?",
    ]
    # Gerar visualização do graph
    for exemplo in exemplos:
        result = exported_graph.invoke(GraphState(input=exemplo, output="", tipo=None))
        print("-" * 100)
        print(f"Pergunta: {exemplo}\nResposta: {result['output']}\nTipo: {result['tipo']}")
        print("-" * 100 + "\n")
