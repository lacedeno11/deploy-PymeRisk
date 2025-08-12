# infrastructure/scoring_agent.py

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# --- Contrato de Entrada ---
class ConsolidatedReport(BaseModel):
    """
    Simula el informe consolidado que el ScoringAgent recibe
    después de que los agentes de negocio han hecho su trabajo.
    """
    financial_summary: str = Field(description="Resumen del análisis financiero (solvencia, liquidez, ventas).")
    reputation_summary: str = Field(description="Resumen del análisis reputacional (sentimiento online, reseñas).")
    behavioral_summary: str = Field(description="Resumen del análisis comportamental (patrones de pago, referencias).")

# --- Contrato de Salida ---
class ScoringResult(BaseModel):
    """
    Define la estructura de la respuesta del ScoringAgent.
    """
    score: int = Field(description="Puntaje de riesgo final, entre 0 y 1000.", ge=0, le=1000)
    justification: str = Field(description="Párrafo explicando cómo se calculó el puntaje y qué factores fueron los más influyentes.")
    recommendation: str = Field(description="Recomendación final: 'Aprobado', 'Rechazado', o 'Requiere Revisión Manual'.")

def generate_score(api_key: str, report: ConsolidatedReport) -> ScoringResult:
    """
    Toma informes consolidados y genera un puntaje de riesgo final y una justificación.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=api_key)
    parser = PydanticOutputParser(pydantic_object=ScoringResult)

    prompt_template = """
    Eres un Director de Riesgos (Chief Risk Officer) de una entidad financiera especializada en PYMEs.
    Tu única tarea es analizar los informes consolidados de tus tres equipos de analistas (Financiero, Reputacional y Comportamental) y generar un único y definitivo puntaje de riesgo de 0 a 1000.

    **RÚBRICA DE PUNTUACIÓN:**
    - Un puntaje por debajo de 400 es ALTO RIESGO (Recomendación: Rechazado).
    - Un puntaje entre 401 y 650 es RIESGO MEDIO (Recomendación: Requiere Revisión Manual).
    - Un puntaje por encima de 650 es BAJO RIESGO (Recomendación: Aprobado).
    - El análisis financiero es el factor más importante (ponderación del 60%). La reputación y el comportamiento tienen una ponderación del 20% cada uno.

    **INFORMES DE LOS ANALISTAS:**

    1.  **Informe Financiero:**
        {financial_summary}

    2.  **Informe Reputacional:**
        {reputation_summary}

    3.  **Informe Comportamental:**
        {behavioral_summary}

    **TU TAREA:**
    Sintetiza los tres informes, aplica la rúbrica de puntuación y la ponderación de factores para calcular el puntaje final. Genera una justificación clara que explique los factores clave que llevaron a ese puntaje.

    **INSTRUCCIONES DE FORMATO:**
    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    # Usamos .dict() para convertir el objeto Pydantic de entrada en un diccionario para el prompt
    scoring_result = chain.invoke(report.model_dump())
    
    return scoring_result