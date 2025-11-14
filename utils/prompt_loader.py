import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("DEVs_AI")


class PromptLoader:
    def __init__(self, config: Dict):
        self.config = config
        self.language_config = config.get("language_specialization", {})
        self.language = self.language_config.get("language", "python")
        self.templates_dir = Path(__file__).parent.parent / "config" / "prompt_templates"
        self._templates_cache = {}

    def get_language_config(self) -> Dict:
        return self.language_config

    def load_template(self, template_name: str) -> Optional[str]:
        template_file = self.templates_dir / f"{self.language}.md"
        
        if not template_file.exists():
            logger.warning(f"Template {template_file} não encontrado, usando template padrão Python")
            template_file = self.templates_dir / "python.md"
            if not template_file.exists():
                logger.error(f"Template padrão Python não encontrado")
                return None

        if template_file in self._templates_cache:
            template_content = self._templates_cache[template_file]
        else:
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_content = f.read()
                self._templates_cache[template_file] = template_content
            except Exception as e:
                logger.error(f"Erro ao carregar template {template_file}: {str(e)}")
                return None

        return self._extract_section(template_content, template_name)

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        lines = content.split("\n")
        in_section = False
        section_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"## {section_name}") or stripped.startswith(f"# {section_name}"):
                in_section = True
                continue
            elif in_section and (stripped.startswith("##") or stripped.startswith("#")):
                if not stripped.startswith(f"## {section_name}") and not stripped.startswith(f"# {section_name}"):
                    break
            elif in_section:
                section_lines.append(line)
        
        if section_lines:
            return "\n".join(section_lines).strip()
        return ""

    def build_prompt(self, template_name: str, context: Dict) -> str:
        template = self.load_template(template_name)
        if not template:
            return ""
        
        lang_config = self.get_language_config()
        replacements = {
            "{LANGUAGE}": lang_config.get("language", "python"),
            "{VERSION}": lang_config.get("version", "3.12+"),
            "{STYLE_GUIDE}": lang_config.get("conventions", {}).get("style_guide", "PEP8"),
            "{TOOLS}": self._format_tools(lang_config.get("tools", {})),
            "{CONVENTIONS}": self._format_conventions(lang_config.get("conventions", {})),
        }
        
        for key, value in context.items():
            replacements[f"{{{key.upper()}}}"] = str(value)
        
        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)
        
        return prompt

    def _format_tools(self, tools: Dict) -> str:
        parts = []
        if tools.get("linter"):
            parts.append(f"Linter: {tools['linter']}")
        if tools.get("formatter"):
            parts.append(f"Formatter: {tools['formatter']}")
        if tools.get("test_framework"):
            parts.append(f"Test Framework: {tools['test_framework']}")
        return ", ".join(parts) if parts else "N/A"

    def _format_conventions(self, conventions: Dict) -> str:
        parts = []
        if conventions.get("style_guide"):
            parts.append(f"Style Guide: {conventions['style_guide']}")
        if conventions.get("type_hints"):
            parts.append("Type Hints: Required")
        if conventions.get("docstring_format"):
            parts.append(f"Docstring Format: {conventions['docstring_format']}")
        return ", ".join(parts) if parts else "N/A"

