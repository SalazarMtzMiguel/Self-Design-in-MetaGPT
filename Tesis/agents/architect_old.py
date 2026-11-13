import sys
import yaml
from pathlib import Path
from loguru import logger
from metagpt.roles.role import Role
from metagpt.actions import Action
from metagpt.configs.llm_config import LLMConfig
from metagpt.schema import Message
# CORRECCIÓN A: Importar explícitamente el objeto config global
from metagpt.config2 import config 

class DesignArchitecture(Action):
    name: str = "DesignArchitecture"

    async def run(self, with_messages: str) -> str:
        # Definimos las reglas del rol
        system_instruction = (

"--- SYSTEM INSTRUCTION ---\n"

"You are a Senior Software Architect specialized in large-scale software systems "
"design.\n\n"
"You are contributing to a Software Design Description (SDD)."
"Your responsibility is to transform system requirements into a complete software "
"architecture. You define the global structure of the system, architectural style, "
"subsystems, responsibilities, and communication strategy.\n\n"

"You must NOT define low-level components, database structures, interfaces, or "
"algorithms. Those tasks belong to specialized engineers.\n\n"


"Your architectural document will be consumed by the Component Engineer.\n\n"


"Generate the architecture using exactly this structure:\n\n"


"1. SYSTEM OVERVIEW:\n"
"Describe the main objectives, scope, and architectural vision of the system.\n\n"


"2. ARCHITECTURAL STYLE:\n"
"Define the recommended architecture pattern (monolith, layered, microservices, "
"event-driven, etc.) and justify the decision.\n\n"


"3. SYSTEM SUBSYSTEMS:\n"
"Identify the main subsystems and define their responsibilities.\n\n"


"4. SYSTEM BOUNDARIES:\n"
"Define what belongs inside the system and external actors/services.\n\n"


"5. COMMUNICATION AND DATA FLOW:\n"
"Explain how information moves through the system during critical operations.\n\n"


"6. ARCHITECTURE INTERACTION DIAGRAM:\n"
"Create a Mermaid sequence diagram showing the global system interaction.\n\n"


"--- OUTPUT CONSTRAINTS ---\n"
"- Be precise and technically rigorous.\n"
"- Do not invent requirements.\n"
"- Do not define implementation details.\n"
"- Preserve traceability with the original requirements.\n"

"Mermaid must be inside a single ```mermaid block.\n"

"--------------------------\n\n"

)
        
        full_prompt = f"{system_instruction}\n\n{with_messages}"
        return await self._aask(prompt=full_prompt)

class ArchitectDesigner(Role):
    name: str = "Alvaro"
    profile: str = "Software Architect"
    goal: str = "Design robust software architectures and generate functional diagrams"
    
    def __init__(self, **data):
        super().__init__(**data)
        
        self.target_model_id = "qwen3.6"
                #self.target_model_id = "local"
        #self.target_model_id = "gemmaOnline"
        selected_llm_config = None
        config_path = Path("config2.yaml") 
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_yaml = yaml.safe_load(f)
                
                llms_dict = raw_yaml.get("llms", {})
                
                if self.target_model_id in llms_dict:
                    llm_data = llms_dict[self.target_model_id]
                    selected_llm_config = LLMConfig(**llm_data)
                    logger.info(f"Cargado exitosamente '{self.target_model_id}' directamente desde config2.yaml")
            except Exception as e:
                logger.error(f"Error al leer el archivo YAML manualmente: {e}")
        else:
            logger.warning("No se encontró el archivo 'config2.yaml' en la raíz del proyecto para la lectura manual.")

        if selected_llm_config:
            self.config.llm = selected_llm_config
        else:
            logger.warning(f"'{self.target_model_id}' no se pudo cargar de 'llms'. Usando el LLM global por defecto.")
        
        self.set_actions([DesignArchitecture(config=self.config)])
    
    def model(self) -> str:
        return self.target_model_id if hasattr(self, 'target_model_id') else "NOT SET"

    async def _act(self) -> Message:
        todo = self.rc.todo
        
        if not self.rc.history:
            raise ValueError(f"El agente {self.name} no ha recibido ningún requerimiento o mensaje para procesar.")
        
        design_context = self.rc.history[-1].content
        
        response = await todo.run(design_context)
        
        msg = Message(content=response, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg