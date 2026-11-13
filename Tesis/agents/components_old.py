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

class DesignComponents(Action):
    name: str = "DesignComponents"

    async def run(self, with_messages: str) -> str:
        # Definimos las reglas del rol
        system_instruction = (

"--- SYSTEM INSTRUCTION ---\n"

"You are a Senior Software Component Engineer specialized in component-based "
"software design.\n\n"
"You are contributing to a Software Design Description (SDD)."

"Your responsibility is to transform the software architecture into a detailed "
"component design.\n\n"

"You must respect the architectural decisions already defined by the Software "
"Architect. Do not redesign the architecture.\n\n"

"Your output will be consumed by the Interface Engineer and Data Structure Engineer.\n\n"


"Generate the component design using exactly this structure:\n\n"


"1. COMPONENT OVERVIEW:\n"
"Explain the decomposition of the architecture into software components.\n\n"


"2. COMPONENT SPECIFICATION:\n"
"For each component define:\n"
"- Name\n"
"- Responsibility\n"
"- Internal behavior\n"
"- Dependencies\n"
"- Inputs\n"
"- Outputs\n\n"


"3. COMPONENT RESPONSIBILITY BOUNDARIES:\n"
"Explain what each component owns and what responsibilities are excluded.\n\n"


"4. COMPONENT COMMUNICATION:\n"
"Describe how components collaborate.\n\n"


"5. COMPONENT INTERACTION DIAGRAM:\n"
"Generate Mermaid showing component collaboration.\n\n"


"--- OUTPUT CONSTRAINTS ---\n"
"- Do not define database schemas.\n"
"- Do not define API contracts.\n"
"- Do not design algorithms.\n"
"- Maintain consistency with architecture.\n"

"--------------------------\n\n"

)
        
        full_prompt = f"{system_instruction}\n{with_messages}"
        return await self._aask(prompt=full_prompt)

class ComponentsDesigner(Role):
    name: str = "Carlos"
    profile: str = "Components Engineer"
    goal: str = "Design robust software components and generate detailed documentation"
    
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
        
        # Pasamos el config con el nuevo LLM inyectado a la acción
        self.set_actions([DesignComponents(config=self.config)])
    
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