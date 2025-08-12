# business_agents/reputational_agent.py

import json
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

# Import Azure OpenAI Service
from ..infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest

class ReputationAnalysisResult(BaseModel):
    """
    Define la estructura del informe generado por el ReputationalAgent.
    """
    sentimiento_general: str = Field(description="El sentimiento general detectado: 'Positivo', 'Neutral', o 'Negativo'.")
    puntaje_sentimiento: float = Field(description="Un puntaje numérico del sentimiento, de -1.0 (muy negativo) a 1.0 (muy positivo).", ge=-1.0, le=1.0)
    temas_positivos: List[str] = Field(description="Una lista de los 3 temas o palabras clave positivas más recurrentes.")
    temas_negativos: List[str] = Field(description="Una lista de los 3 temas o palabras clave negativas más recurrentes.")
    resumen_ejecutivo: str = Field(description="Un párrafo que resume la reputación online general de la empresa.")
    success: bool = Field(description="Indica si el análisis fue exitoso", default=True)
    tokens_used: int = Field(description="Tokens utilizados en el análisis", default=0)

async def analyze_reputation(azure_service, social_media_text: str) -> ReputationAnalysisResult:
    """
    Analiza un cuerpo de texto de redes sociales y extrae un análisis de reputación usando Azure OpenAI.
    """
    try:
        if not social_media_text.strip():
            return ReputationAnalysisResult(
                sentimiento_general="Neutral",
                puntaje_sentimiento=0.0,
                temas_positivos=["No hay datos disponibles"],
                temas_negativos=["No hay datos disponibles"],
                resumen_ejecutivo="No se proporcionaron datos de redes sociales para analizar",
                success=False,
                tokens_used=0
            )

        prompt = f"""
        Eres un especialista en Marketing Digital y Reputación Online (ORM). Tu tarea es analizar un conjunto de comentarios y reseñas sobre una PYME.

        **TEXTO A ANALIZAR (COMENTARIOS Y RESEÑAS):**
        {social_media_text}

        **TU ANÁLISIS:**
        Lee y analiza todo el texto proporcionado para determinar la percepción pública de la empresa. Debes realizar las siguientes tareas:
        1. **Sentimiento General:** Clasifica el sentimiento predominante en el texto como 'Positivo', 'Neutral' o 'Negativo'.
        2. **Puntaje de Sentimiento:** Asigna un puntaje numérico preciso entre -1.0 y 1.0.
        3. **Temas Positivos:** Identifica y lista hasta 3 temas o aspectos que los clientes elogian más.
        4. **Temas Negativos:** Identifica y lista hasta 3 temas o problemas de los que los clientes se quejan más.
        5. **Resumen Ejecutivo:** Escribe un párrafo final que resuma la reputación online general de la empresa y su posicionamiento en el mercado digital.

        Responde ÚNICAMENTE en formato JSON:
        {{
            "sentimiento_general": "<Positivo|Neutral|Negativo>",
            "puntaje_sentimiento": <-1.0 a 1.0>,
            "temas_positivos": ["<tema1>", "<tema2>", "<tema3>"],
            "temas_negativos": ["<tema1>", "<tema2>", "<tema3>"],
            "resumen_ejecutivo": "<resumen detallado>"
        }}
        """

        request = OpenAIRequest(
            request_id=f"reputation_analysis_{datetime.now().strftime('%H%M%S')}",
            user_id="system",
            agent_id="reputational_agent",
            prompt=prompt,
            max_tokens=600,
            temperature=0.1,
            timestamp=datetime.now()
        )

        response = await azure_service.generate_completion(
            request,
            "You are a digital reputation analyst. Provide accurate JSON response.",
            use_mini_model=True  # Use o3-mini for faster sentiment analysis
        )

        # Parse JSON response
        try:
            # Clean the response text first
            response_content = response.response_text.strip()
            
            # Try to extract JSON if it's wrapped in markdown
            if "```json" in response_content:
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                response_content = response_content[start:end].strip()
            elif "```" in response_content:
                start = response_content.find("```") + 3
                end = response_content.find("```", start)
                response_content = response_content[start:end].strip()
            
            result_data = json.loads(response_content)
            return ReputationAnalysisResult(
                sentimiento_general=result_data.get("sentimiento_general", "Neutral"),
                puntaje_sentimiento=float(result_data.get("puntaje_sentimiento", 0.0)),
                temas_positivos=result_data.get("temas_positivos", ["Análisis no disponible"]),
                temas_negativos=result_data.get("temas_negativos", ["Análisis no disponible"]),
                resumen_ejecutivo=result_data.get("resumen_ejecutivo", "Resumen no disponible"),
                success=True,
                tokens_used=response.tokens_used
            )
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract meaningful content from the raw response
            raw_response = response.response_text
            
            # Try to determine sentiment from the raw response
            sentimiento = "Neutral"
            puntaje = 0.0
            
            # Simple sentiment detection
            positive_words = ["excelente", "bueno", "positivo", "recomendado", "calidad", "profesional"]
            negative_words = ["malo", "pésimo", "negativo", "problema", "queja", "deficiente"]
            
            raw_lower = raw_response.lower()
            positive_count = sum(1 for word in positive_words if word in raw_lower)
            negative_count = sum(1 for word in negative_words if word in raw_lower)
            
            if positive_count > negative_count:
                sentimiento = "Positivo"
                puntaje = 0.6
            elif negative_count > positive_count:
                sentimiento = "Negativo"
                puntaje = -0.4
            else:
                sentimiento = "Neutral"
                puntaje = 0.0
            
            return ReputationAnalysisResult(
                sentimiento_general=sentimiento,
                puntaje_sentimiento=puntaje,
                temas_positivos=["Análisis extraído de respuesta no estructurada"],
                temas_negativos=["Ver análisis completo"],
                resumen_ejecutivo=raw_response[:300] + "..." if len(raw_response) > 300 else raw_response,
                success=True,
                tokens_used=response.tokens_used
            )

    except Exception as e:
        return ReputationAnalysisResult(
            sentimiento_general="Neutral",
            puntaje_sentimiento=0.0,
            temas_positivos=[f"Error: {str(e)}"],
            temas_negativos=[f"Error: {str(e)}"],
            resumen_ejecutivo=f"Error en análisis reputacional: {str(e)}",
            success=False,
            tokens_used=0
        )

# Backward compatibility function
def analyze_reputation_legacy(api_key: str, social_media_text: str) -> ReputationAnalysisResult:
    """
    Función de compatibilidad hacia atrás (no recomendada para uso nuevo)
    """
    return ReputationAnalysisResult(
        sentimiento_general="Neutral",
        puntaje_sentimiento=0.0,
        temas_positivos=["Legacy function called - upgrade to use Azure OpenAI Service"],
        temas_negativos=["Legacy function called - upgrade to use Azure OpenAI Service"],
        resumen_ejecutivo="Legacy function called - upgrade to use Azure OpenAI Service",
        success=False,
        tokens_used=0
    )