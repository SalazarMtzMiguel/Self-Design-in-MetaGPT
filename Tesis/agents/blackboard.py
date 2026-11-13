"""Núcleo de memoria compartida y coordinación del sistema multi-agente."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class ArtifactStatus(str, Enum):
    PENDING = "Pendiente"
    IN_PROGRESS = "EnProceso"
    COMPLETED = "Completado"
    REVIEW_REQUESTED = "RevisionSolicitada"
    BLOCKED = "Bloqueado"


@dataclass
class DesignArtifact:
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
class BlackboardMessage:
    sender: str
    message: str
    artifact: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class ProblemTuple:
    problem_id: str
    objective: str
    interaction: str
    knowledge: str
    processing: str
    layer: str
    uncertainty: str

    def as_dict(self) -> dict[str, str]:
        return {
            "objective": self.objective,
            "interaction": self.interaction,
            "knowledge": self.knowledge,
            "processing": self.processing,
            "layer": self.layer,
            "uncertainty": self.uncertainty,
        }


@dataclass(frozen=True)
class ReviewRequest:
    type: str
    artifact: str
    requesting_agent: str
    reason: str
    status: ArtifactStatus


@dataclass
class Blackboard:
    """Cuatro regiones: SES, diseño, problemas y coordinación."""

    ses_data: dict[str, Any] = field(default_factory=dict)
    max_review_iterations: int = 3
    inactivity_timeout_seconds: int = 600
    design_state: dict[str, DesignArtifact] = field(init=False)
    problem_tuples: dict[str, ProblemTuple] = field(default_factory=dict)
    messages: list[BlackboardMessage] = field(default_factory=list)
    coordination: list[ReviewRequest] = field(default_factory=list)
    diagrams: dict[str, str | None] = field(default_factory=dict)

    _responsibilities = {
        "architecture": "ArchitectDesigner",
        "components": "ComponentsInterfacesDesigner",
        "interfaces": "ComponentsInterfacesDesigner",
        "data_structures": "DataStructuresDesigner",
        "storage_schemas": "DataStructuresDesigner",
        "algorithms": "AlgorithmsDesigner",
    }

    def __post_init__(self) -> None:
        if "requirements" not in self.ses_data:
            raise ValueError("ses_data debe incluir requirements.")
        if self.inactivity_timeout_seconds <= 0:
            raise ValueError("inactivity_timeout_seconds debe ser positivo.")
        self.design_state = {
            name: DesignArtifact(
                name=name,
                responsible_agent=agent,
                max_review_iterations=self.max_review_iterations,
            )
            for name, agent in self._responsibilities.items()
        }

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

    def refresh_inactive_artifacts(
        self, now: datetime | None = None
    ) -> list[str]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now debe incluir zona horaria.")
        timeout = timedelta(seconds=self.inactivity_timeout_seconds)
        completed: list[str] = []
        for artifact in self.design_state.values():
            if (
                artifact.content is not None
                and artifact.status
                in {ArtifactStatus.IN_PROGRESS, ArtifactStatus.REVIEW_REQUESTED}
                and current - artifact.last_updated_at >= timeout
            ):
                artifact.status = ArtifactStatus.COMPLETED
                artifact.validated_content = artifact.content
                completed.append(artifact.name)
        return completed

    def read_artifact(self, name: str) -> DesignArtifact:
        self.refresh_inactive_artifacts()
        try:
            return self.design_state[name]
        except KeyError as error:
            raise KeyError(f"Artefacto desconocido: {name}") from error

    def update_artifact(self, name: str, content: Any, agent: str) -> None:
        artifact = self.read_artifact(name)
        if artifact.responsible_agent != agent:
            raise PermissionError(
                f"{agent} no puede modificar '{name}'; responsable: "
                f"{artifact.responsible_agent}."
            )
        if artifact.status is ArtifactStatus.BLOCKED:
            raise RuntimeError(f"El artefacto '{name}' está bloqueado.")
        artifact.content = content
        artifact.status = ArtifactStatus.IN_PROGRESS
        artifact.last_updated_at = datetime.now(timezone.utc)

    def post_message(
        self, sender: str, message: str, artifact: str | None = None
    ) -> BlackboardMessage:
        if not sender.strip() or not message.strip():
            raise ValueError("sender y message no pueden estar vacíos.")
        item = BlackboardMessage(sender, message, artifact)
        self.messages.append(item)
        return item

    def record_problem_tuple(self, problem: ProblemTuple) -> None:
        self.problem_tuples[problem.problem_id] = problem

    def request_review(
        self, name: str, requesting_agent: str, reason: str
    ) -> ReviewRequest:
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
            "SolicitudRevision", name, requesting_agent, reason, status
        )
        self.coordination.append(request)
        self.post_message(requesting_agent, reason, name)
        return request

    def context(self) -> str:
        self.refresh_inactive_artifacts()
        artifacts = "\n\n".join(
            f"{item.name.upper()} [{item.status.value}]:\n{item.content}"
            for item in self.design_state.values()
        )
        tuples = "\n".join(
            f"- {item.problem_id}: {item.as_dict()}"
            for item in self.problem_tuples.values()
        ) or "Ninguna tupla de problema registrada."
        messages = "\n".join(
            f"- [{item.sender}] {item.message}"
            for item in self.messages
        ) or "Sin mensajes."
        return (
            "REGIÓN DE DATOS DEL SES:\n"
            f"{self.ses_data}\n\n"
            "ESTADO DE DISEÑO:\n"
            f"{artifacts}\n\n"
            "REGIÓN DE TUPLAS DE PROBLEMAS:\n"
            f"{tuples}\n\n"
            "REGIÓN DE MENSAJES Y COORDINACIÓN:\n"
            f"{messages}\n\n"
            f"Solicitudes de revisión: {self.coordination}\n"
            f"Diagramas: {self.diagrams}\n"
        )
