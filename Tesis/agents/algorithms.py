"""Agente de algoritmos: consume tuplas y selecciona mediante MCTS."""

from agents.algorithms_old import AlgorithmsDesigner as _LegacyDesigner
from agents.algorithms_old import DesignAlgorithm as _LegacyAction
from agents.llm_config import configure_agent_llm


class DesignAlgorithm(_LegacyAction):
    async def run(self, with_messages: str) -> str:
        instruction = """
Eres el Agente de Algoritmos del sistema de auto-diseño.
Tu entrada principal es la especificación normalizada del problema en tupla
publicada en la región de caracterización de problemas de la pizarra.
Modela la selección como un proceso de decisión y usa MCTS con Thompson
Sampling para explorar alternativas compatibles. No modifiques arquitectura,
componentes, interfaces ni datos. Reporta el algoritmo seleccionado, entradas,
salidas, complejidad, ventajas, limitaciones y trazabilidad con la tupla.
Devuelve exactamente:
1. PROBLEMA COMPUTACIONAL Y TUPLA
2. ALTERNATIVAS COMPATIBLES
3. ESTRATEGIA MCTS Y CRITERIO DE RECOMPENSA
4. ALGORITMO SELECCIONADO
5. TRAZABILIDAD Y RESTRICCIONES
6. DIAGRAMA DEL FLUJO ALGORITMICO
Incluye un bloque Mermaid y no afirmes ejecución si la pizarra registra una
restricción contra MCTS.
"""
        return await self._aask(prompt=f"{instruction}\n{with_messages}")


class AlgorithmsDesigner(_LegacyDesigner):
    def __init__(self, **data):
        super().__init__(**data)
        configure_agent_llm(self)
        self.set_actions([DesignAlgorithm(config=self.config)])


__all__ = ["AlgorithmsDesigner", "DesignAlgorithm"]
