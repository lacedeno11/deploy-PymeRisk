# infrastructure/scenario_simulator.py

from pydantic import BaseModel, Field
from .scoring_agent import ConsolidatedReport, ScoringResult # Importamos los modelos del otro agente
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# --- Contrato de Entrada ---
class SimulationInput(BaseModel):
    """
    Define los datos necesarios para ejecutar una simulación:
    el informe base, el resultado base y el escenario a simular.
    """
    base_report: ConsolidatedReport = Field(description="El informe original con los datos de la empresa.")
    base_score: ScoringResult = Field(description="El resultado del scoring original.")
    scenario_description: str = Field(description="Descripción en lenguaje natural del escenario a simular. Ej: '¿Qué pasaría si la empresa reduce su deuda en $10,000?'")

# --- Contrato de Salida ---
class SimulationResult(BaseModel):
    """
    Define la estructura de la respuesta de una simulación.
    """
    new_score: int = Field(description="El nuevo puntaje de riesgo recalculado bajo el escenario hipotético.", ge=0, le=1000)
    score_change: int = Field(description="La diferencia numérica entre el nuevo puntaje y el original (ej. +50, -30).")
    new_recommendation: str = Field(description="La nueva recomendación basada en el nuevo puntaje.")
    analysis: str = Field(description="Un párrafo explicando por qué el puntaje cambió y el impacto del escenario propuesto.")

def run_simulation(api_key: str, simulation_input: SimulationInput) -> SimulationResult:
    """
    Toma un análisis base y un escenario, y recalcula el riesgo.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=api_key)
    parser = PydanticOutputParser(pydantic_object=SimulationResult)

    prompt_template = """
    Eres un Asesor de Estrategia Financiera para PYMEs. Tu tarea es analizar cómo un escenario hipotético 
    afectaría el puntaje de riesgo de una empresa.

    **CONTEXTO DEL ANÁLISIS ORIGINAL:**
    - **Datos Originales:** {base_report}
    - **Resultado Original:** Puntaje de {base_score_value}, con la recomendación de '{base_recommendation}' y la siguiente justificación: '{base_justification}'

    **ESCENARIO HIPOTÉTICO A EVALUAR:**
    {scenario}

    **TU TAREA:**
    1.  Analiza el impacto del **ESCENARIO HIPOTÉTICO** sobre los **DATOS ORIGINALES**.
    2.  Recalcula el puntaje de riesgo (0-1000) basándote en la rúbrica (Bajo > 650, Medio 401-650, Alto < 400).
    3.  Determina la nueva recomendación.
    4.  Escribe un análisis claro explicando por qué el puntaje cambió, cuantificando el impacto.

    **INSTRUCCIONES DE FORMATO:**
    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    # Preparamos los datos para el prompt
    input_data = {
        "base_report": simulation_input.base_report.model_dump_json(),
        "base_score_value": simulation_input.base_score.score,
        "base_recommendation": simulation_input.base_score.recommendation,
        "base_justification": simulation_input.base_score.justification,
        "scenario": simulation_input.scenario_description
    }

    simulation_result = chain.invoke(input_data)
    
    return simulation_result