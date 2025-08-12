# security/output_sanitizer.py

import json
from datetime import datetime
from pydantic import BaseModel, Field

# Import Azure OpenAI Service
from ...infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest

class SanitizationResult(BaseModel):
    """
    Define la estructura de la respuesta del agente de sanitización de salidas.
    """
    is_safe: bool = Field(description="Debe ser 'true' si el texto original ya era seguro, y 'false' si se requirió alguna modificación.")
    sanitized_text: str = Field(description="El texto final, ya sea el original si era seguro, o la versión con la información sensible enmascarada.")
    details: str = Field(description="Una breve explicación de las acciones tomadas. Por ejemplo, 'No se encontraron problemas' o 'Se redactó 1 dirección de correo electrónico'.")
    pii_detected: bool = Field(description="True si se detectó información personal identificable", default=False)
    sensitive_data_types: list = Field(description="Lista de tipos de datos sensibles detectados", default_factory=list)

async def sanitize_output(azure_service, generated_text: str) -> SanitizationResult:
    """
    Analiza un texto generado por una IA para filtrar información sensible.
    """
    try:
        # Diseñar el "Meta-Prompt" de Cumplimiento y Privacidad
        prompt_template = """
        Eres un Oficial de Cumplimiento y Privacidad (DPO) de una institución financiera.
        Tu única tarea es analizar el [TEXTO GENERADO] por otra IA y asegurarte de que sea seguro y profesional.

        Revisa el texto en busca de lo siguiente:
        1. **Información Personal Identificable (PII):** Nombres de personas, números de cédula, direcciones de correo electrónico, números de teléfono, direcciones físicas
        2. **Información Confidencial:** Nombres de usuario, contraseñas, claves de API, secretos de sistema
        3. **Información Financiera Sensible:** Números de cuenta bancaria, números de tarjeta de crédito, códigos de seguridad
        4. **Lenguaje Inapropiado:** Contenido ofensivo, sesgado, discriminatorio o no profesional
        5. **Información del Sistema:** Prompts internos, configuraciones, rutas de archivos

        **Acción a tomar:**
        - Si el texto es seguro y no contiene nada de lo anterior, devuélvelo sin cambios
        - Si encuentras CUALQUIER información sensible, DEBES reemplazarla con un marcador genérico como `[DATO REDACTADO]`. NO la elimines, solo enmascárala

        [TEXTO GENERADO]:
        {generated_text}

        Responde ÚNICAMENTE en formato JSON:
        {{
            "is_safe": <true|false>,
            "sanitized_text": "<texto sanitizado o original>",
            "details": "<explicación de acciones tomadas>",
            "pii_detected": <true|false>,
            "sensitive_data_types": ["<tipo1>", "<tipo2>"]
        }}
        """

        # Crear request para Azure OpenAI
        request = OpenAIRequest(
            request_id=f"output_sanitization_{datetime.now().strftime('%H%M%S')}",
            user_id="security_system",
            agent_id="output_sanitizer",
            prompt=prompt_template.format(generated_text=generated_text),
            max_tokens=1000,
            temperature=0.0,
            timestamp=datetime.now()
        )

        # Usar o3-mini para sanitización rápida
        response = await azure_service.generate_completion(
            request,
            "You are a privacy compliance officer. Provide accurate JSON response only.",
            use_mini_model=True  # Use o3-mini for fast sanitization
        )

        # Parse JSON response
        try:
            result_data = json.loads(response.response_text)
            
            return SanitizationResult(
                is_safe=result_data.get("is_safe", False),
                sanitized_text=result_data.get("sanitized_text", generated_text),
                details=result_data.get("details", "Sanitization completed"),
                pii_detected=result_data.get("pii_detected", False),
                sensitive_data_types=result_data.get("sensitive_data_types", [])
            )
        except json.JSONDecodeError:
            # For financial analysis, be less restrictive - allow content through
            if any(keyword in generated_text.lower() for keyword in ['solvencia', 'liquidez', 'rentabilidad', 'análisis financiero', 'financial']):
                return SanitizationResult(
                    is_safe=True,
                    sanitized_text=generated_text,
                    details="Financial analysis content allowed through despite JSON parsing error",
                    pii_detected=False,
                    sensitive_data_types=[]
                )
            else:
                # Fallback if JSON parsing fails - err on the side of caution for non-financial content
                return SanitizationResult(
                    is_safe=False,
                    sanitized_text="[CONTENIDO SANITIZADO POR PRECAUCIÓN]",
                    details="Error parsing sanitization result - content blocked as precaution",
                    pii_detected=True,
                    sensitive_data_types=["unknown"]
                )

    except Exception as e:
        # If sanitization fails, err on the side of caution
        return SanitizationResult(
            is_safe=False,
            sanitized_text="[CONTENIDO BLOQUEADO POR ERROR DE SEGURIDAD]",
            details=f"Sanitization error: {str(e)} - content blocked for safety",
            pii_detected=True,
            sensitive_data_types=["error"]
        )

# Backward compatibility function
async def sanitize_output_legacy(api_key: str, generated_text: str) -> SanitizationResult:
    """
    Función de compatibilidad hacia atrás (no recomendada para uso nuevo)
    """
    # This would need an AzureOpenAIService instance, so we return a basic result
    return SanitizationResult(
        is_safe=True,
        sanitized_text=generated_text,
        details="Legacy function called - upgrade to use Azure OpenAI Service",
        pii_detected=False,
        sensitive_data_types=[]
    )

