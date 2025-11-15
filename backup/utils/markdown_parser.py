import json
import re


class MarkdownParseError(Exception):
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


def _parse_markdown_value(value: str) -> any:
    value = value.strip()
    
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"
    
    if value.lower() == "null" or value == "":
        return None
    
    if value.isdigit():
        return int(value)
    
    try:
        if "." in value:
            return float(value)
    except ValueError:
        pass
    
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if inner.isdigit():
            return int(inner)
        try:
            if "." in inner:
                return float(inner)
        except ValueError:
            pass
        items = inner.split(",")
        parsed_items = [_parse_markdown_value(item.strip()) for item in items if item.strip()]
        if len(parsed_items) == 1:
            return parsed_items[0]
        return parsed_items
    
    if value.startswith("{") and value.endswith("}"):
        return _parse_markdown_object(value)
    
    return value


def _parse_markdown_object(obj_str: str) -> dict:
    result = {}
    obj_str = obj_str.strip()
    if not (obj_str.startswith("{") and obj_str.endswith("}")):
        return result
    
    content = obj_str[1:-1].strip()
    if not content:
        return result
    
    depth = 0
    in_string = False
    escape_next = False
    current_key = ""
    current_value = ""
    i = 0
    
    while i < len(content):
        char = content[i]
        
        if escape_next:
            if in_string:
                current_value += char
            escape_next = False
            i += 1
            continue
        
        if char == "\\":
            if in_string:
                current_value += char
            escape_next = True
            i += 1
            continue
        
        if char == '"' or char == "'":
            in_string = not in_string
            if in_string:
                current_value += char
            i += 1
            continue
        
        if in_string:
            current_value += char
            i += 1
            continue
        
        if char == "{":
            depth += 1
            current_value += char
            i += 1
            continue
        
        if char == "}":
            depth -= 1
            current_value += char
            i += 1
            continue
        
        if char == ":" and depth == 0:
            current_key = current_value.strip().strip('"').strip("'")
            current_value = ""
            i += 1
            continue
        
        if char == "," and depth == 0:
            if current_key:
                result[current_key] = _parse_markdown_value(current_value)
            current_key = ""
            current_value = ""
            i += 1
            continue
        
        current_value += char
        i += 1
    
    if current_key:
        result[current_key] = _parse_markdown_value(current_value)
    
    return result


def _extract_markdown_section(content: str, section_title: str) -> str:
    pattern = rf"^##+\s+{re.escape(section_title)}\s*$"
    lines = content.split("\n")
    start_idx = None
    
    for i, line in enumerate(lines):
        if re.match(pattern, line, re.IGNORECASE):
            start_idx = i + 1
            break
    
    if start_idx is None:
        return ""
    
    result_lines = []
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if line.strip().startswith("#") and not line.strip().startswith("###"):
            break
        result_lines.append(line)
    
    return "\n".join(result_lines).strip()


def _parse_list_from_markdown(content: str) -> list:
    items = []
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("- ") or line.startswith("* "):
            item = line[2:].strip()
            items.append(item)
        elif line.startswith("1. ") or re.match(r"^\d+\.\s+", line):
            match = re.match(r"^\d+\.\s+(.+)", line)
            if match:
                items.append(match.group(1).strip())
    
    return items


def _parse_key_value_from_markdown(content: str) -> dict:
    result = {}
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().strip("*").strip()
                value = parts[1].strip().strip("*").strip()
                result[key] = _parse_markdown_value(value)
    
    return result


def _parse_nested_structure(content: str) -> dict:
    result = {}
    lines = content.split("\n")
    current_section = None
    current_subsection = None
    current_content = []
    subsection_content = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if re.match(r"^##\s+", stripped):
            if current_section:
                section_content = "\n".join(current_content).strip()
                if current_subsection:
                    if current_section not in result:
                        result[current_section] = {}
                    result[current_section][current_subsection] = _parse_section_content("\n".join(subsection_content).strip())
                    subsection_content = []
                    current_subsection = None
                else:
                    result[current_section] = _parse_section_content(section_content)
            
            match = re.match(r"^##\s+(.+)$", stripped)
            if match:
                current_section = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
                current_content = []
                current_subsection = None
        elif re.match(r"^###\s+", stripped):
            if current_section and current_subsection:
                if current_section not in result:
                    result[current_section] = {}
                result[current_section][current_subsection] = _parse_section_content("\n".join(subsection_content).strip())
                subsection_content = []
            
            match = re.match(r"^###\s+(.+)$", stripped)
            if match:
                current_subsection = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
                subsection_content = []
        else:
            if current_section:
                if current_subsection:
                    subsection_content.append(line)
                else:
                    current_content.append(line)
        
        i += 1
    
    if current_section:
        if current_subsection:
            if current_section not in result:
                result[current_section] = {}
            result[current_section][current_subsection] = _parse_section_content("\n".join(subsection_content).strip())
        else:
            section_content = "\n".join(current_content).strip()
            result[current_section] = _parse_section_content(section_content)
    
    return result


def _parse_section_content(content: str) -> any:
    if not content:
        return None
    
    content = content.strip()
    
    if content.startswith("-") or content.startswith("*") or re.match(r"^\d+\.\s+", content):
        return _parse_list_from_markdown(content)
    
    if ":" in content:
        if "\n" in content:
            lines_with_colon = [l for l in content.split("\n") if ":" in l]
            if len(lines_with_colon) > 1:
                return _parse_key_value_from_markdown(content)
            else:
                key_value = _parse_key_value_from_markdown(content)
                if len(key_value) == 1:
                    return list(key_value.values())[0]
                return key_value
        else:
            parts = content.split(":", 1)
            if len(parts) == 2:
                return _parse_markdown_value(parts[1].strip())
    
    if content.startswith("```"):
        code_match = re.search(r"```(?:[a-z]+)?\s*(.*?)\s*```", content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
    
    return content


def _extract_markdown_from_code_block(content: str) -> str:
    code_block_match = re.search(r"```(?:markdown)?\s*(.*?)\s*```", content, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    return content


def extract_structured_data_from_markdown(response: str, model_name: str | None = None) -> dict:
    if not response or not response.strip():
        raise MarkdownParseError(
            "Resposta vazia recebida do LLM",
            original_response=response,
            model_name=model_name,
        )
    
    response = response.strip()
    
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(1)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    json_inline_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if json_inline_match:
        try:
            json_str = json_inline_match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    response = _extract_markdown_from_code_block(response)
    
    try:
        result = _parse_nested_structure(response)
        
        if not result:
            result = _parse_key_value_from_markdown(response)
        
        if not result:
            lines = response.split("\n")
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip().strip("*").strip()
                        value = parts[1].strip().strip("*").strip()
                        result[key.lower().replace(" ", "_")] = _parse_markdown_value(value)
        
        if not result:
            raise MarkdownParseError(
                "Não foi possível extrair dados estruturados do Markdown",
                original_response=response,
                model_name=model_name,
            )
        
        return _normalize_structure(result)
    except Exception as e:
        if isinstance(e, MarkdownParseError):
            raise
        raise MarkdownParseError(
            f"Falha ao fazer parse do Markdown: {str(e)}",
            original_response=response,
            original_error=e,
            model_name=model_name,
        ) from e


def _normalize_structure(data: dict) -> dict:
    normalized = {}
    
    for key, value in data.items():
        normalized_key = key.lower().replace(" ", "_").replace("-", "_")
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ["true", "false"]:
                normalized[normalized_key] = value_lower == "true"
            elif value_lower == "null" or value_lower == "":
                normalized[normalized_key] = None
            elif value_lower.isdigit():
                normalized[normalized_key] = int(value_lower)
            elif "." in value_lower and value_lower.replace(".", "").isdigit():
                try:
                    normalized[normalized_key] = float(value_lower)
                except ValueError:
                    normalized[normalized_key] = value
            elif value_lower.startswith("[") and value_lower.endswith("]"):
                inner = value_lower[1:-1].strip()
                if inner.isdigit():
                    normalized[normalized_key] = int(inner)
                else:
                    normalized[normalized_key] = value
            else:
                normalized[normalized_key] = value
        elif isinstance(value, list):
            if len(value) == 1 and isinstance(value[0], (int, float)):
                if normalized_key == "estimated_complexity":
                    normalized[normalized_key] = value[0]
                else:
                    normalized[normalized_key] = [_normalize_value(item) for item in value]
            else:
                normalized[normalized_key] = [_normalize_value(item) for item in value]
        elif isinstance(value, dict):
            normalized[normalized_key] = _normalize_structure(value)
        else:
            normalized[normalized_key] = value
    
    return normalized


def _normalize_value(value: any) -> any:
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ["true", "false"]:
            return value_lower == "true"
        if value_lower == "null" or value_lower == "":
            return None
        if value_lower.isdigit():
            return int(value_lower)
        if "." in value_lower and value_lower.replace(".", "").isdigit():
            try:
                return float(value_lower)
            except ValueError:
                return value
    return value

