"""
Enhanced Azure OpenAI Service with Advanced Rate Limit Handling
Versión mejorada con manejo inteligente de rate limits y optimizaciones
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import openai
from openai import AzureOpenAI

from ..config.azure_config import AzureOpenAIConfig
from .rate_limit_handler import RateLimitHandler, RateLimitConfig, global_rate_limiter


@dataclass
class OpenAIRequest:
    """Solicitud a Azure OpenAI Service"""
    request_id: str
    user_id: str
    agent_id: str
    prompt: str
    max_tokens: int
    temperature: float
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class OpenAIResponse:
    """Respuesta de Azure OpenAI Service"""
    request_id: str
    response_text: str
    tokens_used: int
    processing_time_ms: int
    filtered_content: bool
    confidence_score: float
    timestamp: datetime
    metadata: Dict[str, Any] = None


class EnhancedAzureOpenAIService:
    """
    Servicio Azure OpenAI mejorado con manejo avanzado de rate limits
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint
        )
        
        # Initialize rate limit handler with optimized settings
        rate_limit_config = RateLimitConfig(
            max_retries=8,  # Más intentos para rate limits
            base_delay=2.0,  # Delay base más largo
            max_delay=120.0,  # Delay máximo más largo
            exponential_base=1.8,  # Crecimiento más gradual
            jitter=True,
            rate_limit_window=60,
            max_requests_per_window=40  # Más conservador
        )
        
        self.rate_limiter = RateLimitHandler(rate_limit_config)
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "retried_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
        
        self.logger.info(f"Enhanced Azure OpenAI Service initialized")
        self.logger.info(f"Primary model: {config.deployment_name}")
        self.logger.info(f"Mini model: {config.deployment_name_mini}")
    
    async def generate_completion(self, 
                                request: OpenAIRequest,
                                system_prompt: str = None,
                                use_mini_model: bool = False) -> OpenAIResponse:
        """
        Genera completion con manejo avanzado de rate limits
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        
        try:
            # Apply adaptive delay before making request
            await global_rate_limiter.adaptive_delay()
            
            # Execute with retry logic
            result = await self.rate_limiter.execute_with_retry(
                self._make_openai_request,
                request,
                system_prompt,
                use_mini_model
            )
            
            # Record success
            global_rate_limiter.record_success()
            self.stats["successful_requests"] += 1
            self.stats["total_tokens_used"] += result.tokens_used
            
            # Update average response time
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_average_response_time(processing_time)
            
            return result
            
        except Exception as e:
            # Record failure
            global_rate_limiter.record_failure()
            
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                self.stats["rate_limited_requests"] += 1
            
            self.logger.error(f"Request failed after all retries: {str(e)}")
            raise
    
    async def _make_openai_request(self,
                                  request: OpenAIRequest,
                                  system_prompt: str = None,
                                  use_mini_model: bool = False) -> OpenAIResponse:
        """
        Hace la llamada real a OpenAI (sin retry logic)
        """
        start_time = datetime.now()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        # Select model
        model_to_use = self.config.deployment_name_mini if use_mini_model else self.config.deployment_name
        
        # Prepare parameters based on model type
        params = {
            "model": model_to_use,
            "messages": messages
        }
        
        # o3-mini has different parameter requirements
        if use_mini_model and "o3" in model_to_use.lower():
            params["max_completion_tokens"] = request.max_tokens
        else:
            params.update({
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0
            })
        
        # Log the request
        self.logger.debug(f"Making OpenAI request: {request.request_id} using {model_to_use}")
        
        # Make API call (this is where rate limits can occur)
        response = self.client.chat.completions.create(**params)
        
        # Extract response
        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create response object
        return OpenAIResponse(
            request_id=request.request_id,
            response_text=response_text,
            tokens_used=tokens_used,
            processing_time_ms=int(processing_time),
            filtered_content=False,
            confidence_score=0.95,
            timestamp=datetime.now(),
            metadata={"model": model_to_use}
        )
    
    def _update_average_response_time(self, new_time: float):
        """Actualiza el tiempo promedio de respuesta"""
        if self.stats["successful_requests"] == 1:
            self.stats["average_response_time"] = new_time
        else:
            # Moving average
            current_avg = self.stats["average_response_time"]
            count = self.stats["successful_requests"]
            self.stats["average_response_time"] = ((current_avg * (count - 1)) + new_time) / count
    
    # === MÉTODOS OPTIMIZADOS PARA DIFERENTES TIPOS DE ANÁLISIS ===
    
    async def generate_financial_analysis_optimized(self,
                                                   financial_data: str,
                                                   agent_id: str,
                                                   user_id: str = "system") -> OpenAIResponse:
        """
        Análisis financiero optimizado con prompt más eficiente
        """
        # Prompt optimizado para reducir tokens
        system_prompt = """Eres un analista financiero experto. Analiza datos financieros y responde en JSON con: solvencia, liquidez, rentabilidad, tendencia_ventas, resumen_ejecutivo."""
        
        # Prompt más conciso
        prompt = f"""Analiza estos datos financieros:

{financial_data}

Responde SOLO en JSON:
{{
    "solvencia": "<análisis breve>",
    "liquidez": "<análisis breve>", 
    "rentabilidad": "<análisis breve>",
    "tendencia_ventas": "<análisis breve>",
    "resumen_ejecutivo": "<resumen breve>"
}}"""
        
        request = OpenAIRequest(
            request_id=f"fin_{datetime.now().strftime('%H%M%S')}",
            user_id=user_id,
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=800,  # Reducido para ser más eficiente
            temperature=0.1,
            timestamp=datetime.now()
        )
        
        # Usar GPT-4o para análisis financiero complejo
        return await self.generate_completion(request, system_prompt, use_mini_model=False)
    
    async def generate_reputation_analysis_optimized(self,
                                                    social_data: str,
                                                    agent_id: str,
                                                    user_id: str = "system") -> OpenAIResponse:
        """
        Análisis reputacional optimizado usando o3-mini
        """
        system_prompt = """Eres un analista de reputación digital. Analiza datos de redes sociales y responde en JSON."""
        
        prompt = f"""Analiza esta reputación digital:

{social_data}

Responde SOLO en JSON:
{{
    "sentimiento_general": "<Positivo|Neutral|Negativo>",
    "puntaje_sentimiento": <-1.0 a 1.0>,
    "temas_positivos": ["tema1", "tema2", "tema3"],
    "temas_negativos": ["tema1", "tema2", "tema3"],
    "resumen_ejecutivo": "<resumen breve>"
}}"""
        
        request = OpenAIRequest(
            request_id=f"rep_{datetime.now().strftime('%H%M%S')}",
            user_id=user_id,
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=600,
            temperature=0.1,
            timestamp=datetime.now()
        )
        
        # Usar o3-mini para análisis de sentimiento (más rápido y económico)
        return await self.generate_completion(request, system_prompt, use_mini_model=True)
    
    async def generate_behavioral_analysis_optimized(self,
                                                    behavioral_data: str,
                                                    agent_id: str,
                                                    user_id: str = "system") -> OpenAIResponse:
        """
        Análisis comportamental optimizado usando o3-mini
        """
        system_prompt = """Eres un analista de comportamiento crediticio. Analiza patrones de pago y referencias."""
        
        prompt = f"""Analiza este comportamiento crediticio:

{behavioral_data}

Responde SOLO en JSON:
{{
    "patron_de_pago": "<Puntual|Con Retrasos Leves|Moroso>",
    "fiabilidad_referencias": "<Alta|Media|Baja>",
    "riesgo_comportamental": "<Bajo|Moderado|Alto>",
    "resumen_ejecutivo": "<resumen breve>"
}}"""
        
        request = OpenAIRequest(
            request_id=f"beh_{datetime.now().strftime('%H%M%S')}",
            user_id=user_id,
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=500,
            temperature=0.1,
            timestamp=datetime.now()
        )
        
        # Usar o3-mini para análisis comportamental
        return await self.generate_completion(request, system_prompt, use_mini_model=True)
    
    async def generate_consolidation_optimized(self,
                                             financial_result: Dict[str, Any],
                                             reputational_result: Dict[str, Any],
                                             behavioral_result: Dict[str, Any],
                                             company_name: str,
                                             agent_id: str,
                                             user_id: str = "system") -> OpenAIResponse:
        """
        Consolidación optimizada usando GPT-4o
        """
        system_prompt = """Eres un experto en scoring crediticio. Consolida análisis y genera score final de 0-1000."""
        
        # Prompt más eficiente
        prompt = f"""Consolida estos análisis para {company_name}:

FINANCIERO: {json.dumps(financial_result, ensure_ascii=False)}
REPUTACIONAL: {json.dumps(reputational_result, ensure_ascii=False)}  
COMPORTAMENTAL: {json.dumps(behavioral_result, ensure_ascii=False)}

Responde SOLO en JSON:
{{
    "final_score": <0-1000>,
    "risk_level": "<BAJO|MEDIO|ALTO>",
    "justification": "<justificación breve>",
    "contributing_factors": ["factor1", "factor2", "factor3"],
    "credit_recommendation": "<recomendación breve>",
    "confidence": <0.0-1.0>
}}"""
        
        request = OpenAIRequest(
            request_id=f"cons_{datetime.now().strftime('%H%M%S')}",
            user_id=user_id,
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            timestamp=datetime.now()
        )
        
        # Usar GPT-4o para consolidación compleja
        return await self.generate_completion(request, system_prompt, use_mini_model=False)
    
    # === MÉTODOS DE VALIDACIÓN RÁPIDA ===
    
    async def quick_validation(self,
                              field_name: str,
                              content: str,
                              agent_id: str = "validator") -> OpenAIResponse:
        """
        Validación rápida usando o3-mini
        """
        system_prompt = """Eres un validador de seguridad. Determina si el contenido es seguro para análisis financiero."""
        
        prompt = f"""¿Es seguro este contenido del campo {field_name}?

{content[:500]}...

Responde SOLO en JSON:
{{
    "is_safe": <true|false>,
    "reason": "<razón breve>",
    "confidence": <0.0-1.0>
}}"""
        
        request = OpenAIRequest(
            request_id=f"val_{datetime.now().strftime('%H%M%S')}",
            user_id="system",
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=200,
            temperature=0.0,
            timestamp=datetime.now()
        )
        
        # Usar o3-mini para validación rápida
        return await self.generate_completion(request, system_prompt, use_mini_model=True)
    
    # === MÉTODOS DE ESTADÍSTICAS Y MONITOREO ===
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio"""
        rate_limit_stats = self.rate_limiter.get_rate_limit_stats()
        
        return {
            **self.stats,
            "rate_limit_stats": rate_limit_stats,
            "success_rate": (self.stats["successful_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "rate_limit_rate": (self.stats["rate_limited_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "average_tokens_per_request": self.stats["total_tokens_used"] / max(self.stats["successful_requests"], 1)
        }
    
    def reset_stats(self):
        """Reinicia las estadísticas"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "retried_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
        
        self.logger.info("Service statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica la salud del servicio"""
        try:
            # Test with a minimal request
            test_request = OpenAIRequest(
                request_id="health_check",
                user_id="system",
                agent_id="health_checker",
                prompt="Test",
                max_tokens=5,
                temperature=0.0,
                timestamp=datetime.now()
            )
            
            start_time = datetime.now()
            await self.generate_completion(test_request, use_mini_model=True)
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "endpoint": self.config.endpoint,
                "models_available": [self.config.deployment_name, self.config.deployment_name_mini],
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.config.endpoint,
                "last_check": datetime.now().isoformat()
            }


# Factory function para crear el servicio mejorado
def create_enhanced_azure_service(config: AzureOpenAIConfig = None) -> EnhancedAzureOpenAIService:
    """Crea una instancia del servicio Azure OpenAI mejorado"""
    if config is None:
        config = AzureOpenAIConfig.from_env()
    
    return EnhancedAzureOpenAIService(config)