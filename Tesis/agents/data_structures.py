"""Agente de estructuras de datos alineado con la propuesta."""

from agents.data_structures_old import DataStructuresDesigner as _LegacyDesigner
from agents.data_structures_old import DesignDataStructures as _LegacyAction
from agents.llm_config import configure_agent_llm


class DesignDataStructures(_LegacyAction):
    async def run(self, with_messages: str) -> str:
        instruction = """
Eres el Agente de Estructuras de Datos y Base de Datos.
Lee componentes, interfaces, requisitos y restricciones desde la pizarra.
Define entidades, atributos, relaciones, integridad, persistencia y esquemas
de intercambio sin modificar arquitectura, componentes o interfaces y sin
introducir algoritmos o requisitos nuevos.
Devuelve exactamente:
1. MODELO CONCEPTUAL
2. ENTIDADES, ATRIBUTOS Y RELACIONES
3. PERSISTENCIA Y ESQUEMA DE ALMACENAMIENTO
4. INTEGRIDAD Y RESTRICCIONES
5. ESQUEMAS DE INTERCAMBIO
6. DIAGRAMA DE DATOS
Incluye un bloque Mermaid.
"""
        return await self._aask(prompt=f"{instruction}\n{with_messages}")


class DataStructuresDesigner(_LegacyDesigner):
    def __init__(self, **data):
        super().__init__(**data)
        configure_agent_llm(self)
        self.set_actions([DesignDataStructures(config=self.config)])


__all__ = ["DataStructuresDesigner", "DesignDataStructures"]
