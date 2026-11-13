"""
MCTS semántico guiado por Thompson Sampling para selección de algoritmos en IoT.

Implementa el Algoritmo 6 del Capítulo 8 (O-DMIoT):
    Selección (Thompson) -> Expansión -> Rollout (evaluación de diseños)
    -> Recompensa binaria -> Retropropagación (actualización Beta).

La ontología O-DMIoT se simula con una base de conocimiento en memoria
(clase OntologyKB). Las "consultas de Lógica Descriptiva" se reemplazan por
filtros sobre atributos de cada diseño.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple

Action = Tuple[str, str]            # (dimensión, valor), p. ej. ("approach", "Data_Driven")
DIMENSIONS = ("approach", "technique")  # profundidad máxima del árbol


# ----------------------------------------------------------------------
# 1. "Ontología": diseños candidatos y sus métricas
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Design:
    name: str
    approach: str
    technique: str
    requires: Dict[str, str]        # condiciones del problema para ser compatible
    qoe: float                      # calidad funcional (p. ej. exactitud), en (0, 1]
    latency_ms: float               # QoS: latencia
    complexity: float               # característica del algoritmo: costo en (0, 1]

    def __hash__(self) -> int:
        return hash(self.name)


class OntologyKB:
    """Sustituto mínimo de O-DMIoT: filtra diseños y entrega métricas."""

    def __init__(self, designs: List[Design], rng: random.Random, noise: float = 0.01):
        self.designs = designs
        self.rng = rng
        self.noise = noise
        self._evaluations: Dict[str, Tuple[float, float, float]] = {}  # caché = A-Box
        self.evaluation_requests = 0
        self.cache_hits = 0

    # --- consulta: Design and isDesignForProblem value P and ... ---------
    def compatible_designs(self, problem: Dict[str, str],
                           constraints: FrozenSet[Action]) -> List[Design]:
        out = []
        for d in self.designs:
            if not all(problem.get(k) == v for k, v in d.requires.items()):
                continue                                   # incompatible con el problema
            if all(getattr(d, dim) == val for dim, val in constraints):
                out.append(d)                              # cumple las restricciones del camino
        return out

    # --- FUNCIÓN GENERADORA de acciones semánticamente válidas ----------
    def available_actions(self, problem: Dict[str, str],
                          constraints: FrozenSet[Action]) -> Iterator[Action]:
        """Genera (yield) solo las acciones que dejan al menos un diseño compatible."""
        done = {dim for dim, _ in constraints}
        next_dim = next((d for d in DIMENSIONS if d not in done), None)
        if next_dim is None:
            return                                         # estado terminal: no hay acciones
        seen = set()
        for d in self.compatible_designs(problem, constraints):
            value = getattr(d, next_dim)
            if value not in seen:
                seen.add(value)
                yield (next_dim, value)

    # --- métricas: si no existen se "ejecuta" el algoritmo ---------------
    def metrics(self, d: Design) -> Tuple[float, float, float]:
        self.evaluation_requests += 1
        if d.name not in self._evaluations:                # ejecución bajo demanda (simulada)
            g = self.rng.gauss
            self._evaluations[d.name] = (
                min(1.0, max(0.01, d.qoe + g(0, self.noise))),
                max(0.1, d.latency_ms * (1 + g(0, self.noise))),
                min(1.0, max(0.01, d.complexity + g(0, self.noise))),
            )
        else:
            self.cache_hits += 1
        return self._evaluations[d.name]


@dataclass
class PerformanceMetrics:
    """Métricas observables del rendimiento de una ejecución MCTS."""

    iterations: int = 0
    elapsed_seconds: float = 0.0
    evaluated_designs: int = 0
    explored_nodes: int = 0
    explored_designs: int = 0
    evaluation_requests: int = 0
    cache_hits: int = 0
    best_reward: float = float("-inf")
    best_design: Optional[str] = None
    convergence_iteration: Optional[int] = None

    @property
    def iterations_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.iterations / self.elapsed_seconds

    @property
    def cache_hit_rate(self) -> float:
        if self.evaluation_requests == 0:
            return 0.0
        return self.cache_hits / self.evaluation_requests


# ----------------------------------------------------------------------
# 2. Función de recompensa continua R(d)  (Ec. 8.10)
# ----------------------------------------------------------------------
@dataclass
class RewardWeights:
    w_qoe: float = 0.6
    w_qos: float = 0.3
    w_complexity: float = 0.1


def reward(kb: OntologyKB, d: Design, w: RewardWeights) -> float:
    qoe, latency, complexity = kb.metrics(d)
    f_qoe = qoe                          # ya normalizada en (0, 1]
    f_qos = 1.0 / (1.0 + latency / 10)   # menor latencia -> más cerca de 1
    f_cx = complexity                    # costo: se resta
    return w.w_qoe * f_qoe + w.w_qos * f_qos - w.w_complexity * f_cx


# ----------------------------------------------------------------------
# 3. Nodo del árbol y creencias Beta
# ----------------------------------------------------------------------
@dataclass
class Node:
    constraints: FrozenSet[Action]
    parent: Optional["Node"] = None
    children: Dict[Action, "Node"] = field(default_factory=dict)
    beliefs: Dict[Action, List[float]] = field(default_factory=dict)  # a -> [alpha, beta]
    visits: int = 0

    def belief(self, a: Action) -> List[float]:
        return self.beliefs.setdefault(a, [1.0, 1.0])      # prior uniforme Beta(1,1)


# ----------------------------------------------------------------------
# 4. MCTS con Thompson Sampling
# ----------------------------------------------------------------------
class SemanticMCTS:
    def __init__(self, kb: OntologyKB, problem: Dict[str, str],
                 weights: RewardWeights = RewardWeights(),
                 reward_mode: str = "paper", seed: int = 0):
        """
        reward_mode:
          "paper"    -> r = 1 siempre para el camino que lleva a d* (Ec. 8.12, literal).
          "relative" -> r = 1 solo si R(d*) iguala la mejor recompensa vista hasta ahora;
                        en otro caso r = 0 (así beta sí crece y hay aprendizaje real).
        """
        self.kb, self.problem, self.w = kb, problem, weights
        self.reward_mode = reward_mode
        self.rng = random.Random(seed)
        self.root = Node(constraints=frozenset())
        self.best_seen = float("-inf")
        self.trace: List[dict] = []
        self.metrics = PerformanceMetrics()

    # --- política de Thompson: muestrear theta ~ Beta(a, b), tomar argmax -
    def _thompson(self, node: Node, actions: List[Action]) -> Action:
        samples = {a: self.rng.betavariate(*node.belief(a)) for a in actions}   # Ec. 8.7
        return max(samples, key=samples.get)                                    # Ec. 8.8

    def _is_terminal(self, node: Node) -> bool:
        return not any(True for _ in self.kb.available_actions(self.problem, node.constraints))

    # --- una iteración = un episodio -------------------------------------
    def _iterate(self, i: int) -> None:
        node, path = self.root, []

        # (1) Selección + (2) Expansión
        while not self._is_terminal(node):
            actions = list(self.kb.available_actions(self.problem, node.constraints))
            untried = [a for a in actions if a not in node.children]
            if untried:                                       # expansión (misma política)
                a = self._thompson(node, untried)
                child = Node(node.constraints | {a}, parent=node)
                node.children[a] = child
                path.append((node, a))
                node = child
                break
            a = self._thompson(node, actions)                 # selección
            path.append((node, a))
            node = node.children[a]

        # (3) Rollout: evaluar todos los diseños compatibles con el nodo alcanzado
        candidates = self.kb.compatible_designs(self.problem, node.constraints)
        rewards = {d.name: reward(self.kb, d, self.w) for d in candidates}
        best = max(rewards, key=rewards.get)                  # d*  (Ec. 8.11)
        current_reward = rewards[best]
        if current_reward > self.metrics.best_reward:
            self.metrics.best_reward = current_reward
            self.metrics.best_design = best
            if self.metrics.convergence_iteration is None:
                self.metrics.convergence_iteration = i

        # (4) Recompensa binaria para el camino
        if self.reward_mode == "paper":
            r = 1
        elif self.reward_mode == "relative":
            previous_best = self.best_seen
            r = 1 if rewards[best] > previous_best + 1e-9 else 0
            self.best_seen = max(previous_best, rewards[best])
        else:
            raise ValueError(
                f"Modo de recompensa desconocido: {self.reward_mode!r}. "
                "Use 'paper' o 'relative'."
            )

        # (5) Retropropagación: solo los éxitos actualizan alpha.
        for n, a in path:
            b = n.belief(a)
            if r == 1:
                b[0] += 1
            n.visits += 1

        self.trace.append({"iter": i, "path": [a[1] for _, a in path],
                           "d*": best, "R(d*)": round(current_reward, 3), "r": r})

    def run(self, n_iterations: int) -> Design:
        if n_iterations < 1:
            raise ValueError("n_iterations debe ser mayor que cero.")
        started_at = time.perf_counter()
        for i in range(1, n_iterations + 1):
            self._iterate(i)
        selected = (
            self.best_design()
            if self.reward_mode == "paper"
            else self.best_observed_design()
        )
        self.metrics.iterations = n_iterations
        self.metrics.elapsed_seconds = time.perf_counter() - started_at
        self.metrics.evaluated_designs = len(self.kb._evaluations)
        self.metrics.evaluation_requests = self.kb.evaluation_requests
        self.metrics.cache_hits = self.kb.cache_hits
        self.metrics.explored_nodes = self._count_nodes()
        self.metrics.explored_designs = len(
            {
                trace["d*"]
                for trace in self.trace
            }
        )
        self.metrics.best_design = selected.name
        self.metrics.best_reward = reward(self.kb, selected, self.w)
        return selected

    def _count_nodes(self, node: Optional[Node] = None) -> int:
        node = node or self.root
        return 1 + sum(self._count_nodes(child) for child in node.children.values())

    def performance_report(self) -> Dict[str, object]:
        """Devuelve métricas serializables de la última ejecución."""
        return {
            "iterations": self.metrics.iterations,
            "elapsed_seconds": round(self.metrics.elapsed_seconds, 6),
            "iterations_per_second": round(
                self.metrics.iterations_per_second, 2
            ),
            "evaluated_designs": self.metrics.evaluated_designs,
            "explored_nodes": self.metrics.explored_nodes,
            "explored_designs": self.metrics.explored_designs,
            "evaluation_requests": self.metrics.evaluation_requests,
            "cache_hits": self.metrics.cache_hits,
            "best_design": self.metrics.best_design,
            "best_reward": round(self.metrics.best_reward, 6),
            "convergence_iteration": self.metrics.convergence_iteration,
            "cache_hit_rate": round(self.metrics.cache_hit_rate, 6),
        }

    # --- resultado: seguir las creencias posteriores más altas -----------
    def best_design(self) -> Design:
        node = self.root
        while node.children:
            a = max(node.children,
                    key=lambda x: (node.belief(x)[0] / sum(node.belief(x)), node.belief(x)[0]))
            node = node.children[a]
        cands = self.kb.compatible_designs(self.problem, node.constraints)
        if not cands:
            raise RuntimeError("La política posterior no condujo a un diseño compatible.")
        return max(cands, key=lambda d: reward(self.kb, d, self.w))

    def best_observed_design(self) -> Design:
        if self.metrics.best_design is not None:
            for design in self.kb.designs:
                if design.name == self.metrics.best_design:
                    return design
            raise RuntimeError(
                f"El diseño registrado '{self.metrics.best_design}' "
                "ya no existe en la base de conocimiento."
            )
        raise RuntimeError("No se ha observado ningún diseño.")

    def print_posteriors(self, node: Optional[Node] = None, depth: int = 0) -> None:
        node = node or self.root
        for a, child in node.children.items():
            al, be = node.belief(a)
            print(f"{'   ' * depth}{a[0]}={a[1]:<20} alpha={al:5.0f} beta={be:4.0f} "
                  f"E[theta]={al / (al + be):.3f}")
            self.print_posteriors(child, depth + 1)


# ----------------------------------------------------------------------
# 5. Demostración con el escenario del capítulo (clasificación de cultivos)
# ----------------------------------------------------------------------
def build_demo_kb(rng: random.Random) -> OntologyKB:
    designs = [
        Design("Logistic Regression", "Data_Driven", "Supervised_Learning",
               {"objective": "Classification"}, qoe=0.85, latency_ms=4, complexity=0.15),
        Design("Linear SVM", "Data_Driven", "Supervised_Learning",
               {"objective": "Classification"}, qoe=0.89, latency_ms=9, complexity=0.45),
        Design("k-NN", "Data_Driven", "Instance_Based",
               {"objective": "Classification"}, qoe=0.84, latency_ms=25, complexity=0.60),
        Design("Decision Tree", "Symbolic", "Rule_Induction",
               {"objective": "Classification"}, qoe=0.8, latency_ms=2, complexity=0.20),
        Design("Rule-Based Classifier", "Symbolic", "Expert_Rules",
               {"objective": "Classification"}, qoe=0.66, latency_ms=3, complexity=0.5),
        # Diseños que la ontología descarta para este problema:
        Design("K-Means", "Data_Driven", "Unsupervised_Learning",
               {"objective": "Clustering"}, qoe=0.70, latency_ms=8, complexity=0.30),
        Design("Q-Learning", "Data_Driven", "Reinforcement_Learning",
               {"objective": "Control"}, qoe=0.75, latency_ms=15, complexity=0.50),
    ]
    return OntologyKB(designs, rng)


if __name__ == "__main__":
    problem = {  # estado inicial s0 = (P, {})
        "objective": "Classification", "interaction": "System-driven",
        "knowledge": "Data-driven", "processing": "Centralized",
        "layer": "Application", "uncertainty": "Model uncertainty",
    }

    for mode in ("paper", "relative"):
        print(f"\n===== reward_mode = {mode} =====")
        kb = build_demo_kb(random.Random(42))
        mcts = SemanticMCTS(kb, problem, reward_mode=mode, seed=7)
        best = mcts.run(1000)

        print("Primeras 8 iteraciones:")
        for t in mcts.trace[:8]:
            print("  ", t)
        print("\nCreencias posteriores (Beta):")
        mcts.print_posteriors()
        print(f"\nDiseño seleccionado d* = {best.name}  "
              f"(R = {reward(kb, best, mcts.w):.3f})")
        print("Métricas de rendimiento:")
        for metric, value in mcts.performance_report().items():
            print(f"  {metric}: {value}")