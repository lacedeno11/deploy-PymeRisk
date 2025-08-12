# business_agents/financial_agent.py

import json
from datetime import datetime
from pydantic import BaseModel, Field

# Import Azure OpenAI Service
from ..infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest

class FinancialAnalysisResult(BaseModel):
    """
    Define la estructura del informe generado por el FinancialAgent.
    """
    solvencia: str = Field(description="Análisis de la solvencia de la empresa (capacidad de pago a largo plazo).")
    liquidez: str = Field(description="Análisis de la liquidez (capacidad de pago a corto plazo).")
    rentabilidad: str = Field(description="Análisis de la rentabilidad (capacidad de generar ganancias).")
    tendencia_ventas: str = Field(description="Descripción de la tendencia de las ventas (crecimiento, estancamiento, decrecimiento).")
    resumen_ejecutivo: str = Field(description="Un párrafo final que resume la salud financiera general de la PYME.")
    success: bool = Field(description="Indica si el análisis fue exitoso", default=True)
    tokens_used: int = Field(description="Tokens utilizados en el análisis", default=0)

async def analyze_financial_document(azure_service, document_text: str) -> FinancialAnalysisResult:
    """
    Analiza el texto de un documento financiero y extrae un resumen estructurado usando Azure OpenAI.
    """
    print(f"🏦 INICIANDO ANÁLISIS FINANCIERO")
    print(f"📊 Longitud del documento: {len(document_text)} caracteres")
    print(f"🔧 Tipo de servicio: {type(azure_service).__name__}")
    
    try:
        # Verificar el servicio Azure antes de usarlo
        if not hasattr(azure_service, 'generate_completion'):
            raise Exception(f"Servicio Azure inválido: {type(azure_service)}")

        print(f"✅ Servicio Azure válido: {type(azure_service).__name__}")
        if not document_text.strip():
            print(f"⚠️ DOCUMENTO VACÍO")
            return FinancialAnalysisResult(
                solvencia="No hay datos financieros para analizar",
                liquidez="No hay datos financieros para analizar", 
                rentabilidad="No hay datos financieros para analizar",
                tendencia_ventas="No hay datos financieros para analizar",
                resumen_ejecutivo="No se proporcionaron datos financieros",
                success=False,
                tokens_used=0
            )

        prompt = f"""
        Eres un Analista Financiero Contable experto en Normas Internacionales de Información Financiera (NIIF) para PYMEs en Ecuador.
        Tu tarea es analizar el siguiente texto, extraído de un estado financiero del portal de la Superintendencia de Compañías (SCVS).

        **TEXTO DEL DOCUMENTO FINANCIERO:**
        {document_text}

        **TU ANÁLISIS:**
        Basándote únicamente en el texto proporcionado, realiza un análisis conciso de los siguientes puntos:
        1. **Solvencia:** Evalúa la capacidad de la empresa para cumplir con sus obligaciones a largo plazo.
        2. **Liquidez:** Evalúa la capacidad de la empresa para cubrir sus deudas a corto plazo.
        3. **Rentabilidad:** Evalúa la eficiencia de la empresa para generar beneficios.
        4. **Tendencia de Ventas:** Identifica y describe la evolución de los ingresos o ventas.
        5. **Resumen Ejecutivo:** Proporciona un párrafo final que consolide tu opinión profesional sobre la salud financiera general.

        Responde ÚNICAMENTE en formato JSON:
        {{
            "solvencia": "<análisis detallado>",
            "liquidez": "<análisis detallado>",
            "rentabilidad": "<análisis detallado>",
            "tendencia_ventas": "<análisis detallado>",
            "resumen_ejecutivo": "<resumen ejecutivo>"
        }}
        """

        print(f"📤 ENVIANDO REQUEST A AZURE OPENAI...")
        
        request = OpenAIRequest(
            request_id=f"financial_analysis_{datetime.now().strftime('%H%M%S')}",
            user_id="system",
            agent_id="financial_agent",
            prompt=prompt,
            max_tokens=800,
            temperature=0.1,
            timestamp=datetime.now(),
            metadata={"timeout": 120}  # 2 minutos de timeout
        )

        response = await azure_service.generate_completion(
            request,
            "You are a financial analyst expert. Provide accurate JSON response.",
            use_mini_model=False  # Use GPT-4o for complex financial analysis
        )
        
        print(f"✅ RESPUESTA RECIBIDA DE AZURE OPENAI")
        print(f"📊 Tokens usados: {response.tokens_used}")
        print(f"📝 Longitud de respuesta: {len(response.response_text)} caracteres")

        # Parse JSON response with improved handling
        try:
            # Clean the response text first
            response_content = response.response_text.strip()
            
            # Enhanced JSON extraction from markdown
            if "```json" in response_content.lower():
                # Find the start of JSON content after ```json
                start_pos = response_content.lower().find("```json") + 7
                # Find the end marker
                end_pos = response_content.find("```", start_pos)
                if end_pos != -1:
                    response_content = response_content[start_pos:end_pos].strip()
                else:
                    # No closing ```, take everything after ```json
                    response_content = response_content[start_pos:].strip()
            elif "```" in response_content and "{" in response_content:
                # Find the first { after any ```
                start_marker = response_content.find("```")
                json_start = response_content.find("{", start_marker)
                if json_start != -1:
                    # Find the matching closing }
                    brace_count = 0
                    json_end = json_start
                    for i, char in enumerate(response_content[json_start:], json_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    response_content = response_content[json_start:json_end]
            
            # Clean up any remaining markdown artifacts
            response_content = response_content.replace("```json", "").replace("```", "").strip()
            
            # Remove any leading/trailing whitespace and newlines
            response_content = response_content.strip()
            
            # Try to find JSON object if it's embedded in text
            if not response_content.startswith("{"):
                json_start = response_content.find("{")
                json_end = response_content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    response_content = response_content[json_start:json_end]
            
            result_data = json.loads(response_content)
            return FinancialAnalysisResult(
                solvencia=result_data.get("solvencia", "Análisis no disponible"),
                liquidez=result_data.get("liquidez", "Análisis no disponible"),
                rentabilidad=result_data.get("rentabilidad", "Análisis no disponible"),
                tendencia_ventas=result_data.get("tendencia_ventas", "Análisis no disponible"),
                resumen_ejecutivo=result_data.get("resumen_ejecutivo", "Resumen no disponible"),
                success=True,
                tokens_used=response.tokens_used
            )
        except json.JSONDecodeError as e:
            print(f"🚨 JSON DECODE ERROR: {str(e)}")
            print(f"📝 RESPUESTA RAW: {response.response_text[:500]}...")
            
            # En lugar de devolver "Análisis disponible en respuesta completa"
            # Intenta extraer información útil de la respuesta raw
            raw_response = response.response_text
            
            # Si la respuesta contiene información financiera, úsala
            if any(word in raw_response.lower() for word in ['solvencia', 'liquidez', 'rentabilidad']):
                return FinancialAnalysisResult(
                    solvencia=raw_response[:200] + "...",
                    liquidez=raw_response[:200] + "...",
                    rentabilidad=raw_response[:200] + "...",
                    tendencia_ventas=raw_response[:200] + "...",
                    resumen_ejecutivo=raw_response[:300] + "...",
                    success=True,
                    tokens_used=response.tokens_used
                )
            else:
                # Si no hay información útil, devuelve error claro
                raise Exception(f"Respuesta no contiene análisis financiero válido: {raw_response[:100]}")

    except Exception as e:
        # Log the error for debugging
        print(f"🚨 ERROR EN AGENTE FINANCIERO: {str(e)}")
        print(f"🚨 TIPO DE ERROR: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        return FinancialAnalysisResult(
            solvencia=f"Error en análisis financiero: {str(e)}",
            liquidez=f"Error en análisis financiero: {str(e)}",
            rentabilidad=f"Error en análisis financiero: {str(e)}",
            tendencia_ventas=f"Error en análisis financiero: {str(e)}",
            resumen_ejecutivo=f"Error crítico en análisis financiero: {str(e)}",
            success=False,
            tokens_used=0
        )

# Backward compatibility function
def analyze_financial_document_legacy(api_key: str, document_text: str) -> FinancialAnalysisResult:
    """
    Función de compatibilidad hacia atrás (no recomendada para uso nuevo)
    """
    return FinancialAnalysisResult(
        solvencia="Legacy function called - upgrade to use Azure OpenAI Service",
        liquidez="Legacy function called - upgrade to use Azure OpenAI Service",
        rentabilidad="Legacy function called - upgrade to use Azure OpenAI Service",
        tendencia_ventas="Legacy function called - upgrade to use Azure OpenAI Service",
        resumen_ejecutivo="Legacy function called - upgrade to use Azure OpenAI Service",
        success=False,
        tokens_used=0
    )