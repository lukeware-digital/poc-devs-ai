import json
import re


def _remove_invalid_control_chars(text: str) -> str:
    allowed_control_chars = {"\n", "\r", "\t"}
    result = []
    for char in text:
        if ord(char) < 32:
            if char not in allowed_control_chars:
                continue
        elif ord(char) == 127:
            continue
        result.append(char)
    return "".join(result)


def _extract_json_by_balance(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return text
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == "\\":
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    
    return text[start:]


def _fix_json_strings(json_str: str) -> str:
    result = []
    i = 0
    in_string = False
    escape_next = False
    
    while i < len(json_str):
        char = json_str[i]
        
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue
        
        if char == "\\":
            result.append(char)
            escape_next = True
            i += 1
            continue
        
        if char == '"':
            result.append(char)
            in_string = not in_string
            i += 1
            continue
        
        if in_string:
            if char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            elif ord(char) < 32 and char not in {"\n", "\r", "\t"}:
                result.append(f"\\u{ord(char):04x}")
            elif ord(char) == 127:
                result.append("\\u007f")
            else:
                result.append(char)
        else:
            if ord(char) < 32 and char not in {"\n", "\r", "\t"}:
                pass
            elif ord(char) == 127:
                pass
            else:
                result.append(char)
        
        i += 1
    
    return "".join(result)


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


def _clean_json_string(json_str: str) -> str:
    json_str = _remove_invalid_control_chars(json_str)
    json_str = _fix_json_strings(json_str)
    json_str = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', json_str)
    return json_str.strip()


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
        potential_json = json_match.group(1)
        json_str = _extract_json_by_balance(potential_json)
    else:
        code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
        if code_block_match:
            json_str = _extract_json_by_balance(code_block_match.group(1))
        else:
            json_str = _extract_json_by_balance(response)

    json_str = _clean_json_string(json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e1:
        try:
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e2:
            try:
                json_str = _extract_json_by_balance(response)
                json_str = _clean_json_string(json_str)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
            except json.JSONDecodeError as e3:
                raise JSONParseError(
                    f"Falha ao fazer parse do JSON: {str(e3)}",
                    original_response=response,
                    original_error=e3,
                    model_name=model_name,
                ) from e3
