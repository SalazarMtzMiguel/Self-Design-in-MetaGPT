import yaml
from pathlib import Path
from metagpt.roles.role import Role
from metagpt.actions import Action
from metagpt.configs.llm_config import LLMConfig
from metagpt.schema import Message
from loguru import logger

class DesignAlgorithm(Action):
    name: str = "DesignAlgorithm"

    async def run(self, with_messages: str) -> str:
        system_instruction = (

"--- SYSTEM INSTRUCTION ---\n"

"You are a Senior Algorithm Engineer specialized in algorithm selection and "
"automated software design.\n\n"
"You are contributing to a Software Design Description (SDD)."
"\nYour output is a formal design artifact, not a general explanation.\n"
"Your responsibility is to analyze the complete design state and identify the "
"computational problems that require algorithmic solutions.\n\n"

"You must use algorithmic reasoning and select appropriate algorithms according "
"to the problem characteristics.\n\n"

"When multiple algorithms are possible, evaluate alternatives using a search "
"strategy based on Monte Carlo Tree Search (MCTS).\n\n"

"Use MCTS only when the requirements authorize automatic algorithm selection "
"and execution. If the requirements prohibit MCTS, simulations, automatic "
"selection, or optimization, do not execute or claim that MCTS was used.\n\n"


"Generate the algorithm design using exactly this structure:\n\n"


"1. COMPUTATIONAL PROBLEM IDENTIFICATION:\n"
"Identify the problems requiring algorithmic solutions.\n\n"


"2. ALGORITHM CANDIDATES:\n"
"List possible algorithms and explain their suitability.\n\n"


"3. MCTS SEARCH STRATEGY:\n"
"Explain how MCTS explores and selects the best algorithm candidate.\n\n"


"4. SELECTED ALGORITHMS:\n"
"For each selected algorithm define:\n"
"- Purpose\n"
"- Inputs\n"
"- Outputs\n"
"- Complexity analysis\n"
"- Advantages\n"
"- Limitations\n\n"


"5. ALGORITHM FLOW DIAGRAM:\n"
"Generate Mermaid showing algorithm execution flow.\n\n"


"--- OUTPUT CONSTRAINTS ---\n"
"- Do not redesign architecture.\n"
"- Do not modify components.\n"
"- Do not change data structures.\n"
"- Focus only on algorithm selection and design.\n"

"--------------------------\n\n"

)
        
        full_prompt = f"{system_instruction}\n{with_messages}"
        
        # SINTAXIS V1.0.0: Se pasa únicamente la variable de prompt
        return await self._aask(prompt=full_prompt)

class AlgorithmsDesigner(Role):
    name: str = "Alfredo"
    profile: str = "Algorithm Engineer"
    goal: str = "Translate architectural designs into efficient algorithms"
    
    def __init__(self, **data):
        super().__init__(**data)
        
        #self.target_model_id = "qwen3.6"
        self.target_model_id = "local"
        #self.target_model_id = "gemmaOnline"
        selected_llm_config = None
        
        # 1. Intentar localizar el archivo config2.yaml en la ruta de ejecución actual
        # Modifica "config2.yaml" si tu archivo tiene otro nombre o ruta exacta
        config_path = Path("config2.yaml") 
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_yaml = yaml.safe_load(f)
                
                # Extraemos la sección 'llms' cruda del archivo YAML
                llms_dict = raw_yaml.get("llms", {})
                
                if self.target_model_id in llms_dict:
                    llm_data = llms_dict[self.target_model_id]
                    # Creamos el objeto LLMConfig requerido por MetaGPT con los datos crudos
                    selected_llm_config = LLMConfig(**llm_data)
                    logger.info(f"Cargado exitosamente '{self.target_model_id}' directamente desde config2.yaml")
            except Exception as e:
                logger.error(f"Error al leer el archivo YAML manualmente: {e}")
        else:
            logger.warning("No se encontró el archivo 'config2.yaml' en la raíz del proyecto para la lectura manual.")

        # 2. Inyectar la configuración al agente
        if selected_llm_config:
            self.config.llm = selected_llm_config
        else:
            logger.warning(f"'{self.target_model_id}' no se pudo cargar de 'llms'. Usando el LLM global por defecto.")
        
        self.set_actions([DesignAlgorithm(config=self.config)])
    
    def model(self) -> str:
        return self.target_model_id if hasattr(self, 'target_model_id') else "NOT SET"

    async def _act(self) -> Message:
        todo = self.rc.todo
        context = self.get_memories()
        response = await todo.run(context[-1].content)
        
        msg = Message(content=response, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg