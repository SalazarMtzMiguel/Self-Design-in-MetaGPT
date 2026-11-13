"""Pipeline activo: agentes coordinados mediante la pizarra compartida."""

import asyncio
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.MCTS import SemanticMCTS, build_demo_kb, reward
from agents.algorithms import AlgorithmsDesigner
from agents.architect import ArchitectDesigner
from agents.blackboard import Blackboard, ProblemTuple
from agents.components import ComponentsInterfacesDesigner
from agents.data_structures import DataStructuresDesigner
from metagpt.utils.mermaid import mermaid_to_file


def extract_mermaid(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"```mermaid\s+(.*?)\s+```", text, re.DOTALL)
    return match.group(1) if match else None


def _mcts_restriction(requirements: str) -> str | None:
    normalized = requirements.lower()
    for pattern in (
        r"no utilizar mcts",
        r"no usar mcts",
        r"sin seleccionar automáticamente",
        r"no .*optimización",
    ):
        if re.search(pattern, normalized):
            return pattern
    return None


def run_mcts_from_blackboard(board: Blackboard) -> dict[str, Any]:
    """Ejecuta MCTS a partir de la tupla publicada en la pizarra."""
    requirements = board.ses_data["requirements"]
    restriction = _mcts_restriction(requirements)
    if restriction:
        result = {
            "executed": False,
            "reason": f"MCTS no ejecutado por restricción: {restriction}",
        }
        board.post_message("AlgorithmsDesigner", result["reason"], "algorithms")
        return result

    problem = next(iter(board.problem_tuples.values()), None)
    if problem is None:
        result = {
            "executed": False,
            "reason": "No hay una tupla de problema para activar MCTS.",
        }
        board.post_message("AlgorithmsDesigner", result["reason"], "algorithms")
        return result

    iterations = int(os.environ.get("MCTS_ITERATIONS", "1000"))
    kb = build_demo_kb(random.Random(42))
    mcts = SemanticMCTS(
        kb,
        problem.as_dict(),
        reward_mode="paper",
        seed=7,
    )
    selected = mcts.run(iterations)
    result = {
        "executed": True,
        "problem_id": problem.problem_id,
        "selected_design": selected.name,
        "reward": reward(kb, selected, mcts.w),
        "metrics": mcts.performance_report(),
    }
    board.post_message(
        "AlgorithmsDesigner",
        f"MCTS seleccionó {selected.name}.",
        "algorithms",
    )
    return result


def characterize_requirements(board: Blackboard) -> None:
    """Publica una tupla normalizada para problemas de clasificación."""
    requirements = board.ses_data["requirements"].lower()
    if "clasific" not in requirements and "classification" not in requirements:
        board.post_message(
            "RACR",
            "No se identificó un problema de clasificación.",
            "algorithms",
        )
        return
    board.record_problem_tuple(
        ProblemTuple(
            problem_id="classification",
            objective="Classification",
            interaction="System-driven",
            knowledge="Data-driven",
            processing="Centralized",
            layer="Application",
            uncertainty="Model uncertainty",
        )
    )
    board.post_message(
        "RACR",
        "Tupla normalizada de clasificación publicada para AlgorithmsDesigner.",
        "algorithms",
    )


async def run_thesis_pipeline() -> None:
    root = Path(__file__).resolve().parent
    file_path = root / "Requeriments" / os.environ.get(
        "TESIS_REQUIREMENTS_FILE", "caso2.txt"
    )
    requirements = file_path.read_text(encoding="utf-8")
    board = Blackboard.from_requirement(requirements)
    characterize_requirements(board)

    agents = (
        ("architecture", "ArchitectDesigner", ArchitectDesigner()),
        (
            "components",
            "ComponentsInterfacesDesigner",
            ComponentsInterfacesDesigner(),
        ),
        ("data_structures", "DataStructuresDesigner", DataStructuresDesigner()),
        ("algorithms", "AlgorithmsDesigner", AlgorithmsDesigner()),
    )

    for artifact, agent_name, agent in agents:
        board.post_message(
            "Blackboard",
            f"{agent_name} inicia el procesamiento de {artifact}.",
            artifact,
        )
        message = await agent.run(board.context())
        board.update_artifact(artifact, message.content, agent_name)
        board.diagrams[artifact] = extract_mermaid(message.content)
        if artifact == "components":
            board.update_artifact("interfaces", message.content, agent_name)
            board.diagrams["interfaces"] = extract_mermaid(message.content)
        board.post_message(
            agent_name,
            f"Artefacto {artifact} publicado y en espera de estabilización.",
            artifact,
        )

    mcts_result = run_mcts_from_blackboard(board)
    board.ses_data["mcts"] = mcts_result
    output_dir = root / "output" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / f"{output_dir.name}_resultado_simulacion.txt"
    report.write_text(
        "REGISTRO DE LA PIZARRA\n\n"
        f"{board.context()}\n\n"
        f"RESULTADO MCTS:\n{mcts_result}\n",
        encoding="utf-8",
    )
    for name, diagram in board.diagrams.items():
        if diagram:
            await mermaid_to_file(
                "nodejs", diagram, str(output_dir / f"{output_dir.name}_{name}"),
                suffixes=["svg"],
            )
    print(board.context())
    print(f"Reporte guardado en: {report}")


if __name__ == "__main__":
    asyncio.run(run_thesis_pipeline())
