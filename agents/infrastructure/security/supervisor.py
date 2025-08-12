# security/supervisor.py

import json
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

# Import Azure OpenAI Service
from ...infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest

class SupervisionReport(BaseModel):
    """
    Define la estructura del informe generado por el agente supervisor.
    """
    anomaly_detected: bool = Field(description="Debe ser 'true' si se detectó cualquier patrón anómalo, de lo contrario 'false'.")
    confidence_score: float = Field(description="Confianza en la detección de la anomalía, de 0.0 (ninguna) a 1.0 (certeza total).", ge=0.0, le=1.0)
    summary: str = Field(description="Un resumen en lenguaje natural de los hallazgos. Si no hay anomalías, indicarlo.")
    recommended_action: Literal["Ninguna", "Revisión Manual Requerida", "Alerta de Seguridad Crítica"] = Field(description="La acción recomendada a seguir.")
    critical_alert: bool = Field(description="True si se requiere bloquear operaciones inmediatamente", default=False)

async def run_security_supervision(azure_service, log_file_path: str = "audit.log") -> SupervisionReport:
    """
    Lee los últimos eventos del log de auditoría y los analiza en busca de patrones anómalos.
    """
    # 1. Leer los registros del archivo de log
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Leemos las últimas N líneas para no sobrecargar el análisis
            log_entries = f.readlines()[-100:] 
        
        if not log_entries:
            return SupervisionReport(
                anomaly_detected=False, 
                confidence_score=0.0, 
                summary="El archivo de log está vacío. No hay nada que analizar.", 
                recommended_action="Ninguna",
                critical_alert=False
            )
            
        logs_as_string = "".join(log_entries)
    except FileNotFoundError:
        return SupervisionReport(
            anomaly_detected=True, 
            confidence_score=1.0, 
            summary="Error crítico: El archivo de log 'audit.log' no fue encontrado.", 
            recommended_action="Alerta de Seguridad Crítica",
            critical_alert=True
        )

    try:
        # 2. Diseñar el prompt de auditoría
        prompt_template = """
        Eres un Analista de Ciberseguridad de un Centro de Operaciones de Seguridad (SOC) especializado en sistemas de IA.
        Tu tarea es analizar el siguiente lote de registros de auditoría y detectar patrones de actividad sospechosos o anómalos.

        Busca patrones como:
        - Múltiples intentos de validación fallidos (VALIDATION_FAILURE) desde una misma fuente o en un corto período de tiempo
        - Un pico inusual de errores (ERROR o CRITICAL)
        - Actividad repetitiva y rápida que podría indicar un ataque automatizado (bot)
        - Intentos de prompt injection o bypass de seguridad
        - Patrones que se desvíen de un comportamiento normal de uso
        - Múltiples evaluaciones fallidas consecutivas
        - Acceso desde IPs sospechosas o patrones de acceso anómalos

        [LOGS DE AUDITORÍA]:
        {log_data}

        Responde ÚNICAMENTE en formato JSON:
        {{
            "anomaly_detected": <true|false>,
            "confidence_score": <0.0-1.0>,
            "summary": "<resumen detallado de hallazgos>",
            "recommended_action": "<Ninguna|Revisión Manual Requerida|Alerta de Seguridad Crítica>",
            "critical_alert": <true|false>
        }}
        """

        # 3. Crear request para Azure OpenAI
        request = OpenAIRequest(
            request_id=f"security_supervision_{datetime.now().strftime('%H%M%S')}",
            user_id="security_system",
            agent_id="security_supervisor",
            prompt=prompt_template.format(log_data=logs_as_string),
            max_tokens=500,
            temperature=0.0,
            timestamp=datetime.now()
        )

        # 4. Usar GPT-4o para análisis complejo de seguridad
        response = await azure_service.generate_completion(
            request,
            "You are a cybersecurity analyst. Provide accurate JSON response only.",
            use_mini_model=False  # Use GPT-4o for complex security analysis
        )

        # 5. Parse JSON response
        try:
            result_data = json.loads(response.response_text)
            
            # Determine critical alert based on recommended action
            critical_alert = result_data.get("recommended_action") == "Alerta de Seguridad Crítica"
            
            return SupervisionReport(
                anomaly_detected=result_data.get("anomaly_detected", False),
                confidence_score=result_data.get("confidence_score", 0.0),
                summary=result_data.get("summary", "Error parsing supervision result"),
                recommended_action=result_data.get("recommended_action", "Revisión Manual Requerida"),
                critical_alert=critical_alert
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return SupervisionReport(
                anomaly_detected=True,
                confidence_score=0.5,
                summary="Error parsing security supervision result - flagged for manual review",
                recommended_action="Revisión Manual Requerida",
                critical_alert=False
            )

    except Exception as e:
        # If supervision fails, err on the side of caution
        return SupervisionReport(
            anomaly_detected=True,
            confidence_score=0.8,
            summary=f"Security supervision error: {str(e)} - flagged for immediate review",
            recommended_action="Alerta de Seguridad Crítica",
            critical_alert=True
        )

# Backward compatibility function
async def run_security_supervision_legacy(api_key: str, log_file_path: str = "audit.log") -> SupervisionReport:
    """
    Función de compatibilidad hacia atrás (no recomendada para uso nuevo)
    """
    # This would need an AzureOpenAIService instance, so we return a basic report
    return SupervisionReport(
        anomaly_detected=False,
        confidence_score=0.0,
        summary="Legacy function called - upgrade to use Azure OpenAI Service",
        recommended_action="Ninguna",
        critical_alert=False
    )