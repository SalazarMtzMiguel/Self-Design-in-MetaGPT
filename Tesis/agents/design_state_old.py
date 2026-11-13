"""Backward-compatible import for the shared design blackboard."""

from agents.blackboard import Blackboard


class DesignState(Blackboard):
    """Compatibility wrapper for callers that still construct DesignState."""

    def __init__(self, requirement: str, **kwargs):
        super().__init__(ses_data={"requirements": requirement}, **kwargs)