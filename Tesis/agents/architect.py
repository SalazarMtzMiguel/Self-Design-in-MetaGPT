"""Agente de arquitectura alineado con la propuesta de auto-diseño."""

from agents.architect_old import ArchitectDesigner as _LegacyArchitect
from agents.architect_old import DesignArchitecture as _LegacyAction
from agents.llm_config import configure_agent_llm


class DesignArchitecture(_LegacyAction):
    async def run(self, with_messages: str) -> str:
        instruction = """
Eres el Agente de Arquitectura del sistema multi-agente de auto-diseño.
Lee la región SES, el tipo de transformación y el estado de la pizarra.
Analiza mantenimiento, evolución por cambio de problema o metamorfosis.
Define la arquitectura objetivo sin diseñar componentes internos, bases de
datos, contratos concretos ni algoritmos de implementación.
Devuelve exactamente:
1. VISION GENERAL
2. ESTILO Y VISTAS ARQUITECTONICAS
3. SUBSISTEMAS Y RESPONSABILIDADES
4. LIMITES DEL SISTEMA
5. COMUNICACION Y FLUJO DE INFORMACION
6. DIAGRAMA DE INTERACCION
Incluye un bloque Mermaid. Conserva los elementos válidos en evolución y
descarta la arquitectura previa solo en metamorfosis.
"""
        return await self._aask(prompt=f"{instruction}\n{with_messages}")


class ArchitectDesigner(_LegacyArchitect):
    def __init__(self, **data):
        super().__init__(**data)
        configure_agent_llm(self)
        self.set_actions([DesignArchitecture(config=self.config)])


__all__ = ["ArchitectDesigner", "DesignArchitecture"]
