"""Agente unificado de componentes e interfaces."""

from agents.components_old import ComponentsDesigner as _LegacyDesigner
from agents.components_old import DesignComponents as _LegacyAction
from agents.llm_config import configure_agent_llm


class DesignComponents(_LegacyAction):
    async def run(self, with_messages: str) -> str:
        instruction = """
Eres el Agente de Componentes e Interfaces del sistema de auto-diseño.
Refina la arquitectura publicada en la pizarra identificando componentes,
responsabilidades, dependencias, entradas y salidas, y define sus interfaces.
No modifiques decisiones arquitectónicas, no agregues requisitos, no diseñes
estructuras de datos ni algoritmos.
Devuelve exactamente:
1. COMPONENTES Y RESPONSABILIDADES
2. COMPORTAMIENTO Y DEPENDENCIAS
3. CONTRATOS DE INTERFAZ
4. PROTOCOLOS, VALIDACION Y ERRORES
5. LIMITES DE RESPONSABILIDAD
6. DIAGRAMA DE COMPONENTES E INTERFACES
Incluye un bloque Mermaid y mantén consistencia con la pizarra.
"""
        return await self._aask(prompt=f"{instruction}\n{with_messages}")


class ComponentsInterfacesDesigner(_LegacyDesigner):
    def __init__(self, **data):
        super().__init__(**data)
        configure_agent_llm(self)
        self.set_actions([DesignComponents(config=self.config)])


ComponentsDesigner = ComponentsInterfacesDesigner
__all__ = ["ComponentsInterfacesDesigner", "ComponentsDesigner", "DesignComponents"]
