"""Configuración compartida del LLM para todos los agentes activos."""

import os
from pathlib import Path

import yaml
from loguru import logger
from metagpt.configs.llm_config import LLMConfig


DEFAULT_LLM_NAME = "local"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config2.yaml"


def load_llm_config(name: str | None = None) -> tuple[str, LLMConfig | None]:
    """Carga el LLM nombrado en ``config2.yaml`` o usa el global por defecto."""
    selected_name = name or os.getenv("TESIS_LLM_NAME", DEFAULT_LLM_NAME)
    if not CONFIG_PATH.exists():
        logger.warning("No se encontró la configuración del LLM en {}", CONFIG_PATH)
        return selected_name, None

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file) or {}
        llms = raw_config.get("llms", {})
        llm_data = llms.get(selected_name)
        if llm_data is None:
            raise KeyError(f"El LLM '{selected_name}' no existe en 'llms'.")
        return selected_name, LLMConfig(**llm_data)
    except (OSError, KeyError, TypeError, ValueError) as error:
        logger.error("No se pudo cargar el LLM '{}': {}", selected_name, error)
        return selected_name, None


def configure_agent_llm(agent: object) -> None:
    """Aplica la configuración global al rol activo."""
    name, llm = load_llm_config()
    setattr(agent, "target_model_id", name)
    if llm is not None:
        agent.config.llm = llm
