# infrastructure/orchestrator.py

import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# ¡Importación clave! Usaremos la clase BaseTool de CrewAI.
from crewai_tools import BaseTool

from .scoring_agent import ConsolidatedReport, ScoringResult, generate_score

# --- Paso 1: Definir nuestras herramientas como clases que heredan de BaseTool ---

class FinancialAnalysisTool(BaseTool):
    name: str = "Financial Analysis Tool"
    description: str = "Útil para realizar un análisis financiero detallado de una empresa. La entrada debe ser el nombre de la empresa."

    def _run(self, company_name: str) -> str:
        print(f"DEBUG: Herramienta Financiera ejecutada para {company_name}.")
        return "La empresa muestra un crecimiento de ventas del 20%, pero su liquidez es ajustada."

class ReputationalAnalysisTool(BaseTool):
    name: str = "Reputational Analysis Tool"
    description: str = "Útil para realizar un análisis de la reputación online de una empresa. La entrada debe ser el nombre de la empresa."

    def _run(self, company_name: str) -> str:
        print(f"DEBUG: Herramienta Reputacional ejecutada para {company_name}.")
        return "El sentimiento en redes es mayormente positivo, con excelentes reseñas."

class BehavioralAnalysisTool(BaseTool):
    name: str = "Behavioral Analysis Tool"
    description: str = "Útil para realizar un análisis del comportamiento comercial y de pagos. La entrada debe ser el nombre de la empresa."

    def _run(self, company_name: str) -> str:
        print(f"DEBUG: Herramienta Comportamental ejecutada para {company_name}.")
        return "El historial de pagos a proveedores es impecable."

class ScoringTool(BaseTool):
    name: str = "Scoring Tool"
    description: str = "Útil para consolidar resúmenes y generar un puntaje de riesgo final. La entrada debe ser un string con los 3 resúmenes."

    def _run(self, summaries: str) -> str:
        # El LLM aprenderá a pasar los resúmenes como un solo string.
        # En un caso real, podríamos hacer que esta herramienta sea más estructurada.
        # Por ahora, extraemos los datos para nuestro mock.
        financial_summary, reputation_summary, behavioral_summary = summaries.split('\n')[:3]
        
        api_key = os.getenv("OPENAI_API_KEY")
        report = ConsolidatedReport(
            financial_summary=financial_summary,
            reputation_summary=reputation_summary,
            behavioral_summary=behavioral_summary
        )
        result: ScoringResult = generate_score(api_key=api_key, report=report)
        return result.model_dump_json()

# --- Paso 2: Instanciar nuestras nuevas herramientas ---
financial_tool = FinancialAnalysisTool()
reputational_tool = ReputationalAnalysisTool()
behavioral_tool = BehavioralAnalysisTool()
scoring_tool = ScoringTool()

# --- El resto del código es idéntico a antes ---
def run_orchestration_crew(company_name: str, api_key: str):
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=api_key)

    # Definimos los agentes y les pasamos las instancias de nuestras nuevas clases de herramientas
    financial_analyst = Agent(role='Analista Financiero Senior', goal=f'...', backstory='...', tools=[financial_tool], llm=llm, verbose=True)
    reputation_analyst = Agent(role='Analista de Reputación Digital', goal=f'...', backstory='...', tools=[reputational_tool], llm=llm, verbose=True)
    behavioral_analyst = Agent(role='Analista de Comportamiento Comercial', goal=f'...', backstory='...', tools=[behavioral_tool], llm=llm, verbose=True)
    risk_director = Agent(role='Director de Riesgos', goal=f'...', backstory='...', tools=[scoring_tool], llm=llm, verbose=True)

    # Las tareas se definen igual, pero ahora los agentes usarán sus nuevas herramientas
    financial_task = Task(description=f"Realizar un análisis financiero para {company_name}.", agent=financial_analyst, expected_output="Un resumen conciso de una frase sobre la salud financiera.")
    reputation_task = Task(description=f"Realizar un análisis de reputación online para {company_name}.", agent=reputation_analyst, expected_output="Un resumen conciso de una frase sobre la reputación online.")
    behavioral_task = Task(description=f"Realizar un análisis de comportamiento comercial para {company_name}.", agent=behavioral_analyst, expected_output="Un resumen conciso de una frase sobre el comportamiento comercial.")
    
    scoring_task = Task(
        description=f"Tomar los resúmenes de los análisis financiero, reputacional y comportamental para {company_name} y consolidarlos en un puntaje final.",
        agent=risk_director,
        context=[financial_task, reputation_task, behavioral_task],
        expected_output='Un string en formato JSON con el puntaje, justificación y recomendación final.'
    )

    crew = Crew(
        agents=[financial_analyst, reputation_analyst, behavioral_analyst, risk_director],
        tasks=[financial_task, reputation_task, behavioral_task, scoring_task],
        process=Process.sequential,
        verbose=2
    )

    result = crew.kickoff()
    return result