import re
from typing import Any

from langchain.messages import AIMessage, HumanMessage
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

# Modelo
llm = ChatOllama(model="llama3.2:3b")


# State
class GraphState(BaseModel):
    input: str = Field(description="O input do usuário")
    output: str = Field(default="", description="A resposta do modelo")
    messages: list[Any] = Field(default_factory=list, description="Histórico de mensagens")


# Função para determinar qual nó chamar
def router(state: GraphState) -> str:
    input_text = state.input.lower()

    if "somar" in input_text or "+" in input_text or "adicionar" in input_text:
        return "somar"
    elif "dividir" in input_text or "/" in input_text:
        return "dividir"
    else:
        return "resposta_direta"


# Função de resposta direta
def resposta_direta(state: GraphState) -> GraphState:
    input_message = state.input
    output = llm.invoke([HumanMessage(content=input_message)])
    return GraphState(input=state.input, output=output.content, messages=state.messages + [output])


# Função para somar
def somar_node(state: GraphState) -> GraphState:
    # Extrair números do input

    numbers = re.findall(r"\d+", state.input)
    if len(numbers) >= 2:
        valores = ",".join(numbers)
        resultado = somar(valores)
        output = f"A soma de {', '.join(numbers)} é {resultado}"
    else:
        output = "Não consegui identificar números para somar no seu pedido."

    return GraphState(input=state.input, output=output, messages=state.messages + [AIMessage(content=output)])


# Função para dividir
def dividir_node(state: GraphState) -> GraphState:
    numbers = re.findall(r"\d+", state.input)
    if len(numbers) >= 2:
        valores = ",".join(numbers[:2])
        resultado = dividir(valores)
        output = f"A divisão de {numbers[0]} por {numbers[1]} é {resultado}"
    else:
        output = "Não consegui identificar dois números para dividir no seu pedido."

    return GraphState(input=state.input, output=output, messages=state.messages + [AIMessage(content=output)])


def somar(valores: str) -> str:
    valores_list = valores.split(",")
    try:
        valores_float = [float(valor.strip()) for valor in valores_list]
        return str(sum(valores_float))
    except ValueError:
        return "Erro: todos os valores devem ser números"


def dividir(valores: str) -> str:
    valores_list = valores.split(",")
    try:
        if len(valores_list) < 2:
            return "Erro: são necessários pelo menos dois números para divisão"
        numerador = float(valores_list[0].strip())
        denominador = float(valores_list[1].strip())
        if denominador == 0:
            return "Erro: divisão por zero"
        return str(numerador / denominador)
    except ValueError:
        return "Erro: todos os valores devem ser números"


# Construção do grafo corrigida
graph = StateGraph(GraphState)

# Adicionando nós
graph.add_node("resposta_direta", resposta_direta)
graph.add_node("somar", somar_node)
graph.add_node("dividir", dividir_node)

# Configurando as rotas
graph.add_conditional_edges(
    START, router, {"resposta_direta": "resposta_direta", "somar": "somar", "dividir": "dividir"}
)

# Todas as rotas levam ao fim
graph.add_edge("resposta_direta", END)
graph.add_edge("somar", END)
graph.add_edge("dividir", END)

# Compilando o grafo
exported_graph = graph.compile()


if __name__ == "__main__":
    # Gerar visualização do grafo
    try:
        png_draw_method = exported_graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
        with open("graph.png", "wb") as f:
            f.write(png_draw_method)
        print("Grafo salvo como graph.png")
    except Exception as e:
        print(f"Erro ao gerar grafo: {e}")

    test_cases = ["Quanto é 2+2?", "Divida 10 por 2", "Quem pintou a Mona Lisa?", "Some 5, 10 e 15"]

    for test_input in test_cases:
        print(f"\nInput: {test_input}")
        result = exported_graph.invoke({"input": test_input})
        print(f"Resposta: {result['output']}")
