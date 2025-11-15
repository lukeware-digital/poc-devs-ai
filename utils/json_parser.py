import json
import re


class JSONParseError(Exception):
    def __init__(
        self,
        message: str,
        original_response: str = "",
        original_error: Exception | None = None,
        model_name: str | None = None,
    ):
        super().__init__(message)
        self.original_response = original_response
        self.response_length = len(original_response) if original_response else 0
        self.first_chars = original_response[:200] if original_response else ""
        self.last_chars = original_response[-200:] if original_response else ""
        self.model_name = model_name
        self.original_error = original_error

    def __str__(self) -> str:
        details = [super().__str__()]
        if self.model_name:
            details.append(f"Modelo: {self.model_name}")
        details.append(f"Tamanho da resposta: {self.response_length} caracteres")
        if self.original_error:
            details.append(f"Erro original: {str(self.original_error)}")
        if self.first_chars:
            details.append(f"Primeiros caracteres: {self.first_chars}")
        if self.last_chars and self.response_length > 200:
            details.append(f"Últimos caracteres: {self.last_chars}")
        return " | ".join(details)


def extract_json_from_response(response: str, model_name: str | None = None) -> dict:
    if not response or not response.strip():
        raise JSONParseError(
            "Resposta vazia recebida do LLM",
            original_response=response,
            model_name=model_name,
        )

    response = response.strip()

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_start = response.find("{")
        json_end = response.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_str = response[json_start : json_end + 1]
        else:
            json_str = response

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise JSONParseError(
            f"Falha ao fazer parse do JSON: {str(e)}",
            original_response=response,
            original_error=e,
            model_name=model_name,
        ) from e
