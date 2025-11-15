from langchain.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

# Modelo
llm = ChatOllama(model="gemma3:4b")


# State
class GraphState(BaseModel):
    input: str = Field(description="O input do usuário")
    output: str = Field(default="", description="A resposta do modelo")


# Função de resposta
def response(state: GraphState) -> GraphState:
    input_message = state.input
    output = llm.invoke([HumanMessage(content=input_message)])
    return GraphState(input=state.input, output=output.content)


# StateGraph
graph = StateGraph(GraphState)
graph.add_node("responder", response)
graph.set_entry_point("responder")
graph.set_finish_point("responder")

# Compilando o graph
exported_graph = graph.compile()

# Executando o graph
if __name__ == "__main__":
    result = exported_graph.invoke(GraphState(input="Quem descobriu a América?"))
    print(result["output"])

    # Visualizando o graph
    print(exported_graph.get_graph().draw_mermaid())
