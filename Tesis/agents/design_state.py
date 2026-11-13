"""Compatibilidad para código que todavía importa DesignState."""

from agents.blackboard import Blackboard


class DesignState(Blackboard):
    """Alias compatible con el núcleo de coordinación actual."""

    def __init__(self, requirement: str, **kwargs):
        super().__init__(ses_data={"requirements": requirement}, **kwargs)
