```mermaid
flowchart TD
    %% Entradas y Salidas
    InputReq["Requerimientos de Tesis (reqs.txt)"]
    OutputSys["Salidas del Sistema (Reporte TXT y SVG)"]

    %% Repositorio del Estado del Sistema (DesignState)
    subgraph Repo [Repositorio: Estado del Sistema]
        DesignState[("Objeto DesignState")]
        
        %% Variables en memoria
        subgraph Memoria [Variables en Memoria]
            reqData["requirement"]
            archData["architecture"]
            compData["components"]
            intData["interfaces"]
            structData["data_structures"]
            algoData["algorithms"]
            diagData["diagrams (dict)"]
        end
    end

    %% Pipeline Multi-Agente
    subgraph Pipeline [Pipeline de Agentes]
        Phase1["Fase 1: Inicializacion"]
        Phase2["Fase 2: Architect Designer"]
        Phase3["Fase 3: Components Designer"]
        Phase4["Fase 4: Interfaces Designer"]
        Phase5["Fase 5: Data Struct Designer"]
        Phase6["Fase 6: Algorithms Designer"]
        Phase7["Fase 7: Renderizado y Reporte"]
    end

    %% Flujo de ejecución secuencial y peticiones al Repositorio
    InputReq --> Phase1
    
    %% Fase 1
    Phase1 -->|Guarda reqs iniciales| reqData
    Phase1 --> Phase2
    
    %% Fase 2
    DesignState -.->|Lee context| Phase2
    Phase2 -->|Escribe architecture| archData
    Phase2 -->|Guarda mermaid| diagData
    Phase2 --> Phase3
    
    %% Fase 3
    DesignState -.->|Lee context| Phase3
    Phase3 -->|Escribe components| compData
    Phase3 -->|Guarda mermaid| diagData
    Phase3 --> Phase4
    
    %% Fase 4
    DesignState -.->|Lee context| Phase4
    Phase4 -->|Escribe interfaces| intData
    Phase4 -->|Guarda mermaid| diagData
    Phase4 --> Phase5
    
    %% Fase 5
    DesignState -.->|Lee context| Phase5
    Phase5 -->|Escribe data_structures| structData
    Phase5 -->|Guarda mermaid| diagData
    Phase5 --> Phase6
    
    %% Fase 6
    DesignState -.->|Lee context| Phase6
    Phase6 -->|Escribe algorithms| algoData
    Phase6 -->|Guarda mermaid| diagData
    Phase6 --> Phase7
    
    %% Fase 7
    DesignState -.->|Lee contexto y diagramas| Phase7
    Phase7 -->|Genera Archivos| OutputSys

    %% Definicion de Estilos
    classDef stateRepo fill:#fdfefe,stroke:#2c3e50,stroke-width:3px,color:#2c3e50
    classDef agent fill:#ebf5fb,stroke:#2980b9,stroke-width:2px,color:#154360
    classDef io fill:#f5eef8,stroke:#8e44ad,stroke-width:2px,color:#4a235a
    classDef mem fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#0e6251

    %% Aplicacion de Estilos
    class InputReq,OutputSys io
    class DesignState stateRepo
    class reqData,archData,compData,intData,structData,algoData,diagData mem
    class Phase1,Phase2,Phase3,Phase4,Phase5,Phase6,Phase7 agent
    ```