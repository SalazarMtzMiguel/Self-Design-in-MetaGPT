"""Agente de interfaces activo; conserva el comportamiento original."""

from agents.interfaces_old import InterfacesDesigner as _LegacyDesigner
from agents.interfaces_old import DesignInterfaces
from agents.llm_config import configure_agent_llm


class InterfacesDesigner(_LegacyDesigner):
    def __init__(self, **data):
        super().__init__(**data)
        configure_agent_llm(self)


__all__ = ["InterfacesDesigner", "DesignInterfaces"]
