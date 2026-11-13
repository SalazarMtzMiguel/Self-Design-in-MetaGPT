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

class DesignDataStructures(Action):
    name: str = "DesignDataStructures"

    async def run(self, with_messages: str) -> str:
        # Definimos las reglas del rol
        system_instruction = (

"--- SYSTEM INSTRUCTION ---\n"

"You are a Senior Data Structure Engineer specialized in software data modeling.\n\n"

"You are contributing to a Software Design Description (SDD)."
"Your responsibility is to transform interface requirements into data models "
"and storage structures.\n\n"

"You must preserve previous architectural, component, and interface decisions.\n\n"


"Your output will be consumed by the Algorithm Engineer.\n\n"


"Generate the data design using exactly this structure:\n\n"


"1. DATA MODEL OVERVIEW:\n"
"Explain the data organization strategy.\n\n"


"2. DOMAIN ENTITIES:\n"
"For each entity define:\n"
"- Name\n"
"- Attributes\n"
"- Relationships\n"
"- Constraints\n\n"


"3. DATA STORAGE DESIGN:\n"
"Define database strategy and persistence approach.\n\n"


"4. DATA CONSISTENCY RULES:\n"
"Define transactions, validation, and integrity constraints.\n\n"


"5. DATA MODEL DIAGRAM:\n"
"Generate Mermaid entity relationship diagram.\n\n"


"--- OUTPUT CONSTRAINTS ---\n"
"- Do not define algorithms.\n"
"- Do not modify interfaces.\n"
"- Maintain consistency with previous artifacts.\n"

"--------------------------\n\n"

)
        
        full_prompt = f"{system_instruction}\n{with_messages}"
        return await self._aask(prompt=full_prompt)

class DataStructuresDesigner(Role):
    name: str = "Daniel"
    profile: str = "Data Structures Designer"
    goal: str = "Design efficient data structures and generate detailed documentation"
    
    def __init__(self, **data):
        super().__init__(**data)
        self.target_model_id = "qwen3.6"
        #self.target_model_id = "local"
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
        
        # Pasamos el config con el nuevo LLM inyectado a la acción
        self.set_actions([DesignDataStructures(config=self.config)])
    
    def model(self) -> str:
        return self.target_model_id if hasattr(self, 'target_model_id') else "NOT SET"

    async def _act(self) -> Message:
        todo = self.rc.todo
        
        # CORRECCIÓN B: Validación defensiva de memoria/historial de mensajes entrantes
        # MetaGPT v1.0+ almacena la secuencia de trabajo en self.rc.history
        if not self.rc.history:
            raise ValueError(f"El agente {self.name} no ha recibido ningún requerimiento o mensaje para procesar.")
            
        # Obtenemos el último mensaje seguro
        context = self.rc.history[-1].content
        
        # Ejecutamos la acción enviando la instrucción limpia
        response = await todo.run(context)
        
        msg = Message(content=response, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg