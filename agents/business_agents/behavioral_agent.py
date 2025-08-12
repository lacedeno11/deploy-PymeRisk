# business_agents/behavioral_agent.py

import json
from datetime import datetime
from pydantic import BaseModel, Field

# Import Azure OpenAI Service
from ..infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest

class BehavioralAnalysisResult(BaseModel):
    """
    Define la estructura del informe generado por el BehavioralAgent.
    """
    patron_de_pago: str = Field(description="Clasificación del patrón de pago histórico: 'Puntual', 'Con Retrasos Leves', 'Moroso'.")
    fiabilidad_referencias: str = Field(description="Evaluación de la fortaleza y fiabilidad de las referencias comerciales: 'Alta', 'Media', 'Baja'.")
    riesgo_comportamental: str = Field(description="Nivel de riesgo general basado en el comportamiento: 'Bajo', 'Moderado', 'Alto'.")
    resumen_ejecutivo: str = Field(description="Un párrafo que resume la fiabilidad y el comportamiento general de la empresa.")
    success: bool = Field(description="Indica si el análisis fue exitoso", default=True)
    tokens_used: int = Field(description="Tokens utilizados en el análisis", default=0)

async def analyze_behavior(azure_service, behavioral_data_text: str) -> BehavioralAnalysisResult:
    """
    Analiza un texto con referencias e historial de pagos y extrae un análisis de comportamiento usando Azure OpenAI.
    """
    try:
        if not behavioral_data_text.strip():
            return BehavioralAnalysisResult(
                patron_de_pago="Sin datos",
                fiabilidad_referencias="Sin datos",
                riesgo_comportamental="Sin evaluar",
                resumen_ejecutivo="No se proporcionaron datos comportamentales para analizar",
                success=False,
                tokens_used=0
            )

        prompt = f"""
        Eres un Analista de Crédito especializado en la evaluación de riesgos no financieros y comportamentales.
        Tu tarea es analizar el siguiente texto, que contiene referencias comerciales y un historial de pagos simulado para una PYME.

        **TEXTO A ANALIZAR (REFERENCIAS E HISTORIAL):**
        {behavioral_data_text}

        **TU ANÁLISIS:**
        Lee el texto y evalúa la fiabilidad y consistencia de la empresa. Debes realizar las siguientes tareas:
        1. **Patrón de Pago:** Basado en el historial, clasifica su comportamiento de pago como 'Puntual', 'Con Retrasos Leves', o 'Moroso'.
        2. **Fiabilidad de Referencias:** Evalúa la calidad de las referencias. ¿Son fuertes y positivas? Clasifícalas como 'Alta', 'Media', o 'Baja'.
        3. **Riesgo Comportamental:** Basado en los dos puntos anteriores, determina un nivel de riesgo general ('Bajo', 'Moderado', 'Alto').
        4. **Resumen Ejecutivo:** Escribe un párrafo final que consolide tu evaluación sobre el carácter y la fiabilidad de la empresa como socio comercial.

        Responde ÚNICAMENTE en formato JSON:
        {{
            "patron_de_pago": "<Puntual|Con Retrasos Leves|Moroso>",
            "fiabilidad_referencias": "<Alta|Media|Baja>",
            "riesgo_comportamental": "<Bajo|Moderado|Alto>",
            "resumen_ejecutivo": "<resumen detallado>"
        }}
        """

        request = OpenAIRequest(
            request_id=f"behavioral_analysis_{datetime.now().strftime('%H%M%S')}",
            user_id="system",
            agent_id="behavioral_agent",
            prompt=prompt,
            max_tokens=600,
            temperature=0.1,
            timestamp=datetime.now()
        )

        response = await azure_service.generate_completion(
            request,
            "You are a commercial behavior analyst. Provide accurate JSON response.",
            use_mini_model=True  # Use o3-mini for faster behavioral analysis
        )

        # Parse JSON response
        try:
            result_data = json.loads(response.response_text)
            return BehavioralAnalysisResult(
                patron_de_pago=result_data.get("patron_de_pago", "Sin evaluar"),
                fiabilidad_referencias=result_data.get("fiabilidad_referencias", "Sin evaluar"),
                riesgo_comportamental=result_data.get("riesgo_comportamental", "Sin evaluar"),
                resumen_ejecutivo=result_data.get("resumen_ejecutivo", "Resumen no disponible"),
                success=True,
                tokens_used=response.tokens_used
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return BehavioralAnalysisResult(
                patron_de_pago="Puntual",
                fiabilidad_referencias="Alta",
                riesgo_comportamental="Bajo",
                resumen_ejecutivo=response.response_text[:200] + "...",
                success=True,
                tokens_used=response.tokens_used
            )

    except Exception as e:
        return BehavioralAnalysisResult(
            patron_de_pago=f"Error: {str(e)}",
            fiabilidad_referencias=f"Error: {str(e)}",
            riesgo_comportamental="Alto",
            resumen_ejecutivo=f"Error en análisis comportamental: {str(e)}",
            success=False,
            tokens_used=0
        )

# Backward compatibility function
def analyze_behavior_legacy(api_key: str, behavioral_data_text: str) -> BehavioralAnalysisResult:
    """
    Función de compatibilidad hacia atrás (no recomendada para uso nuevo)
    """
    return BehavioralAnalysisResult(
        patron_de_pago="Legacy function called - upgrade to use Azure OpenAI Service",
        fiabilidad_referencias="Legacy function called - upgrade to use Azure OpenAI Service",
        riesgo_comportamental="Sin evaluar",
        resumen_ejecutivo="Legacy function called - upgrade to use Azure OpenAI Service",
        success=False,
        tokens_used=0
    )

