"""Shared blackboard used to coordinate the software design agents."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class ArtifactStatus(str, Enum):
    """Lifecycle states for a design artifact."""

    PENDING = "Pendiente"
    IN_PROGRESS = "EnProceso"
    COMPLETED = "Completado"
    REVIEW_REQUESTED = "RevisionSolicitada"
    BLOCKED = "Bloqueado"


@dataclass
class DesignArtifact:
    """A design artifact and the information needed to control its revisions."""

    name: str
    responsible_agent: str
    content: Any = None
    status: ArtifactStatus = ArtifactStatus.PENDING
    revision_count: int = 0
    max_review_iterations: int = 3
    validated_content: Any = None
    last_updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def stabilized(self) -> bool:
        return (
            self.status is ArtifactStatus.COMPLETED
            and self.content == self.validated_content
        )


@dataclass(frozen=True)
class ReviewRequest:
    """A request to reopen an artifact without changing it directly."""

    type: str
    artifact: str
    requesting_agent: str
    reason: str
    status: ArtifactStatus


@dataclass(frozen=True)
class ProblemCharacterization:
    """Normalized description of a problem that may require an algorithm."""

    problem_id: str
    description: str
    normalized_tuple: tuple[Any, ...]


@dataclass
class Blackboard:
    """Central shared memory for SES data, design, problems, and coordination."""

    ses_data: dict[str, Any] = field(default_factory=dict)
    max_review_iterations: int = 3
    inactivity_timeout_seconds: int = 600
    design_state: dict[str, DesignArtifact] = field(init=False)
    diagrams: dict[str, str | None] = field(default_factory=dict)
    problem_characterization: dict[str, ProblemCharacterization] = field(
        default_factory=dict
    )
    coordination: list[ReviewRequest] = field(default_factory=list)

    _artifact_responsibilities = {
        "architecture": "ArchitectDesigner",
        "components": "ComponentsDesigner",
        "interfaces": "InterfacesDesigner",
        "data_structures": "DataStructuresDesigner",
        "storage_schemas": "DataStructuresDesigner",
        "algorithms": "AlgorithmsDesigner",
    }

    def __post_init__(self) -> None:
        if self.inactivity_timeout_seconds <= 0:
            raise ValueError("inactivity_timeout_seconds debe ser mayor que cero.")
        self.design_state = {
            name: DesignArtifact(
                name=name,
                responsible_agent=responsible_agent,
                max_review_iterations=self.max_review_iterations,
            )
            for name, responsible_agent in self._artifact_responsibilities.items()
        }
        if "requirements" not in self.ses_data:
            raise ValueError("ses_data debe incluir la información de requirements.")

    @classmethod
    def from_requirement(
        cls, requirement: str, *, max_review_iterations: int = 3
    ) -> "Blackboard":
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError("requirement debe ser una cadena no vacía.")
        return cls(
            ses_data={"requirements": requirement},
            max_review_iterations=max_review_iterations,
        )

    def read_artifact(self, name: str) -> DesignArtifact:
        self.refresh_inactive_artifacts()
        try:
            return self.design_state[name]
        except KeyError as error:
            raise KeyError(f"Artefacto desconocido: {name}") from error

    def update_artifact(self, name: str, content: Any, agent: str) -> None:
        self.refresh_inactive_artifacts()
        artifact = self.read_artifact(name)
        if agent != artifact.responsible_agent:
            raise PermissionError(
                f"{agent} no puede modificar el artefacto '{name}'. "
                f"Responsable: {artifact.responsible_agent}."
            )
        if artifact.status is ArtifactStatus.BLOCKED:
            raise RuntimeError(f"El artefacto '{name}' está bloqueado.")

        artifact.content = content
        artifact.status = ArtifactStatus.IN_PROGRESS
        artifact.last_updated_at = datetime.now(timezone.utc)

    def refresh_inactive_artifacts(
        self, now: datetime | None = None
    ) -> list[str]:
        """Complete reviewable artifacts that have been idle for ten minutes."""
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now debe incluir zona horaria.")
        completed: list[str] = []
        timeout = timedelta(seconds=self.inactivity_timeout_seconds)
        for artifact in self.design_state.values():
            if (
                artifact.status in {
                    ArtifactStatus.IN_PROGRESS,
                    ArtifactStatus.REVIEW_REQUESTED,
                }
                and artifact.content is not None
                and current_time - artifact.last_updated_at >= timeout
            ):
                artifact.status = ArtifactStatus.COMPLETED
                artifact.validated_content = artifact.content
                completed.append(artifact.name)
        return completed

    def request_review(self, name: str, requesting_agent: str, reason: str) -> ReviewRequest:
        if not reason.strip():
            raise ValueError("reason debe ser una justificación no vacía.")
        artifact = self.read_artifact(name)
        if artifact.status is ArtifactStatus.BLOCKED:
            status = ArtifactStatus.BLOCKED
        elif artifact.revision_count >= artifact.max_review_iterations:
            artifact.status = ArtifactStatus.BLOCKED
            status = ArtifactStatus.BLOCKED
        else:
            artifact.revision_count += 1
            artifact.status = ArtifactStatus.REVIEW_REQUESTED
            status = ArtifactStatus.REVIEW_REQUESTED
        artifact.last_updated_at = datetime.now(timezone.utc)

        request = ReviewRequest(
            type="SolicitudRevision",
            artifact=name,
            requesting_agent=requesting_agent,
            reason=reason,
            status=status,
        )
        self.coordination.append(request)
        return request

    def characterize_problem(
        self,
        problem_id: str,
        description: str,
        normalized_tuple: tuple[Any, ...],
    ) -> ProblemCharacterization:
        if not problem_id.strip() or not description.strip():
            raise ValueError("problem_id y description no pueden estar vacíos.")
        if not normalized_tuple:
            raise ValueError("normalized_tuple no puede estar vacío.")
        problem = ProblemCharacterization(
            problem_id=problem_id,
            description=description,
            normalized_tuple=normalized_tuple,
        )
        self.problem_characterization[problem_id] = problem
        return problem

    def context(self) -> str:
        """Return a read-only textual snapshot suitable for agent prompts."""
        self.refresh_inactive_artifacts()
        artifacts = "\n\n".join(
            f"{artifact.name.upper()} [{artifact.status.value}]:\n"
            f"{artifact.content}"
            for artifact in self.design_state.values()
        )
        problems = "\n".join(
            f"- {problem.problem_id}: {problem.description} "
            f"| tuple={problem.normalized_tuple}"
            for problem in self.problem_characterization.values()
        ) or "Ningún problema caracterizado."
        coordination = "\n".join(
            f"- {request.type}: {request.artifact} | "
            f"{request.requesting_agent} | {request.status.value} | "
            f"{request.reason}"
            for request in self.coordination
        ) or "Sin solicitudes de revisión."

        return (
            "REGIÓN DE DATOS DEL SES:\n"
            f"{self.ses_data}\n\n"
            "ESTADO DE DISEÑO:\n"
            f"{artifacts}\n\n"
            "DIAGRAMAS:\n"
            f"{self.diagrams}\n\n"
            "CARACTERIZACIÓN DE PROBLEMAS:\n"
            f"{problems}\n\n"
            "REGIÓN DE COORDINACIÓN:\n"
            f"{coordination}\n"
        )
