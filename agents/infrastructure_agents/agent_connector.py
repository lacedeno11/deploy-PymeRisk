"""
Agent Connector - Interfaz Central para Conexión con Modelos y Agentes
Archivo principal para conectar con GPT-4o, o3-mini y todos los agentes del sistema
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .config.azure_config import AzureInfrastructureConfig
from .services.azure_openai_service import AzureOpenAIService, OpenAIRequest, OpenAIResponse
from .services.azure_sql_service import AzureSQLService, RiskEvaluation, AgentResult, ScoringDetail
from .services.azure_blob_service import AzureBlobService
from .services.semantic_kernel_service import SemanticKernelService


class ModelType(Enum):
    """Tipos de modelo disponibles"""
    GPT4O = "gpt-4o"           # Para análisis complejos
    O3_MINI = "o3-mini"        # Para tareas rápidas/económicas
    AUTO = "auto"              # Selección automática


class TaskComplexity(Enum):
    """Niveles de complejidad de tareas"""
    SIMPLE = "simple"          # Validaciones, extracciones simples
    MODERATE = "moderate"      # Clasificaciones, resúmenes
    COMPLEX = "complex"        # Análisis profundos, razonamiento complejo


class AgentType(Enum):
    """Tipos de agentes en el sistema"""
    SECURITY = "security"              # Agentes de seguridad
    BUSINESS = "business"              # Agentes de negocio
    INFRASTRUCTURE = "infrastructure"  # Agentes de infraestructura


@dataclass
class AgentRequest:
    """Solicitud para un agente específico"""
    agent_id: str
    agent_type: AgentType
    task_type: str
    input_data: Dict[str, Any]
    complexity: TaskComplexity = TaskComplexity.MODERATE
    model_preference: ModelType = ModelType.AUTO
    max_tokens: int = 2000
    temperature: float = 0.3
    user_id: str = "system"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Respuesta de un agente"""
    agent_id: str
    agent_type: AgentType
    task_type: str
    success: bool
    result_data: Dict[str, Any]
    model_used: str
    tokens_used: int
    processing_time_ms: int
    confidence_score: float
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentConnector:
    """
    Conector Central para Agentes y Modelos
    
    Proporciona una interfaz unificada para:
    - Conectar con GPT-4o y o3-mini
    - Ejecutar agentes de seguridad, negocio e infraestructura
    - Gestionar el flujo de datos entre agentes
    - Optimizar el uso de modelos según complejidad
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = AzureInfrastructureConfig()
        
        # Initialize services
        self.openai_service: Optional[AzureOpenAIService] = None
        self.sql_service: Optional[AzureSQLService] = None
        self.blob_service: Optional[AzureBlobService] = None
        self.semantic_kernel_service: Optional[SemanticKernelService] = None
        
        # Agent registry
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        
        # Model usage statistics
        self.model_stats = {
            "gpt4o_requests": 0,
            "o3mini_requests": 0,
            "total_tokens": 0,
            "total_cost_estimate": 0.0
        }
        
        self.logger.info("AgentConnector initialized")
    
    async def initialize(self) -> bool:
        """Inicializa todos los servicios"""
        try:
            self.logger.info("Initializing AgentConnector services...")
            
            # Initialize OpenAI Service
            self.openai_service = AzureOpenAIService(self.config.openai)
            
            # Initialize SQL Service (optional)
            try:
                self.sql_service = AzureSQLService(self.config.sql_database)
            except Exception as e:
                self.logger.warning(f"SQL Service not available: {e}")
            
            # Initialize Blob Service (optional)
            try:
                self.blob_service = AzureBlobService(self.config.blob_storage)
            except Exception as e:
                self.logger.warning(f"Blob Service not available: {e}")
            
            # Initialize Semantic Kernel Service (optional)
            try:
                self.semantic_kernel_service = SemanticKernelService(
                    self.config.semantic_kernel, 
                    self.config.openai
                )
            except Exception as e:
                self.logger.warning(f"Semantic Kernel Service not available: {e}")
            
            self.logger.info("AgentConnector services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AgentConnector: {e}")
            return False
    
    # === MODEL SELECTION AND EXECUTION ===
    
    def select_optimal_model(self, task_complexity: TaskComplexity, 
                           task_type: str, 
                           model_preference: ModelType = ModelType.AUTO) -> ModelType:
        """Selecciona el modelo óptimo según la complejidad de la tarea"""
        
        if model_preference != ModelType.AUTO:
            return model_preference
        
        # Tareas que siempre usan o3-mini (rápido y económico)
        simple_tasks = [
            "validation", "data_extraction", "format_conversion",
            "simple_classification", "quick_check", "summary"
        ]
        
        # Tareas que siempre usan GPT-4o (análisis complejo)
        complex_tasks = [
            "financial_analysis", "risk_assessment", "scenario_analysis",
            "strategic_planning", "explanation_generation", "complex_reasoning"
        ]
        
        # Selección por tipo de tarea
        if task_type in simple_tasks or task_complexity == TaskComplexity.SIMPLE:
            return ModelType.O3_MINI
        elif task_type in complex_tasks or task_complexity == TaskComplexity.COMPLEX:
            return ModelType.GPT4O
        else:
            # Para tareas moderadas, usar o3-mini por defecto (más económico)
            return ModelType.O3_MINI
    
    async def execute_with_model(self, 
                               prompt: str,
                               system_prompt: str,
                               model_type: ModelType,
                               max_tokens: int = 2000,
                               temperature: float = 0.3,
                               agent_id: str = "unknown",
                               user_id: str = "system") -> OpenAIResponse:
        """Ejecuta una solicitud con el modelo especificado"""
        
        if not self.openai_service:
            raise RuntimeError("OpenAI service not initialized")
        
        # Create request
        request = OpenAIRequest(
            request_id=f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            agent_id=agent_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timestamp=datetime.now(),
            metadata={"model_type": model_type.value}
        )
        
        # Execute with appropriate model
        use_mini = (model_type == ModelType.O3_MINI)
        response = await self.openai_service.generate_completion(
            request, system_prompt, use_mini_model=use_mini
        )
        
        # Update statistics
        if use_mini:
            self.model_stats["o3mini_requests"] += 1
        else:
            self.model_stats["gpt4o_requests"] += 1
        
        self.model_stats["total_tokens"] += response.tokens_used
        
        return response
    
    # === AGENT EXECUTION METHODS ===
    
    async def execute_agent(self, request: AgentRequest) -> AgentResponse:
        """Ejecuta un agente específico con optimización automática de modelo"""
        
        start_time = datetime.now()
        
        try:
            # Select optimal model
            optimal_model = self.select_optimal_model(
                request.complexity, 
                request.task_type, 
                request.model_preference
            )
            
            # Get agent-specific prompt and system prompt
            agent_prompts = self._get_agent_prompts(request.agent_id, request.task_type)
            
            # Format prompt with input data
            formatted_prompt = agent_prompts["user_prompt"].format(
                input_data=json.dumps(request.input_data, indent=2, ensure_ascii=False),
                task_type=request.task_type,
                **request.input_data
            )
            
            # Execute with selected model
            response = await self.execute_with_model(
                prompt=formatted_prompt,
                system_prompt=agent_prompts["system_prompt"],
                model_type=optimal_model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                agent_id=request.agent_id,
                user_id=request.user_id
            )
            
            # Parse response
            try:
                result_data = json.loads(response.response_text)
            except json.JSONDecodeError:
                # If not JSON, wrap in result object
                result_data = {
                    "result": response.response_text,
                    "raw_response": True
                }
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create agent response
            agent_response = AgentResponse(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                task_type=request.task_type,
                success=True,
                result_data=result_data,
                model_used=optimal_model.value,
                tokens_used=response.tokens_used,
                processing_time_ms=int(processing_time),
                confidence_score=response.confidence_score,
                timestamp=datetime.now(),
                metadata={
                    "model_selected": optimal_model.value,
                    "complexity": request.complexity.value,
                    "filtered_content": response.filtered_content
                }
            )
            
            # Save to database if available
            if self.sql_service:
                await self._save_agent_result(request, agent_response)
            
            self.logger.info(f"Agent {request.agent_id} executed successfully with {optimal_model.value}")
            return agent_response
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            error_response = AgentResponse(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                task_type=request.task_type,
                success=False,
                result_data={"error": str(e)},
                model_used="none",
                tokens_used=0,
                processing_time_ms=int(processing_time),
                confidence_score=0.0,
                timestamp=datetime.now(),
                error_message=str(e)
            )
            
            self.logger.error(f"Agent {request.agent_id} execution failed: {e}")
            return error_response
    
    def _get_agent_prompts(self, agent_id: str, task_type: str) -> Dict[str, str]:
        """Obtiene los prompts específicos para cada agente"""
        
        # Prompts por tipo de agente
        agent_prompts = {
            # === SECURITY AGENTS ===
            "input_validator": {
                "system_prompt": """
                Eres un validador de entrada especializado en datos financieros de PYMEs.
                Tu tarea es validar que los datos de entrada sean completos, consistentes y realistas.
                Responde siempre en formato JSON con: status, errors, warnings, validated_data.
                """,
                "user_prompt": """
                Valida los siguientes datos de entrada para evaluación de riesgo:
                
                Datos: {input_data}
                
                Verifica:
                1. Completitud de campos requeridos
                2. Consistencia de valores numéricos
                3. Rangos realistas para el sector
                4. Formato correcto de datos
                
                Responde en JSON con: {{"status": "valid/invalid", "errors": [], "warnings": [], "validated_data": {{}}}}
                """
            },
            
            "security_supervisor": {
                "system_prompt": """
                Eres un supervisor de seguridad que verifica la integridad y seguridad de los datos.
                Detectas anomalías, datos sospechosos y posibles intentos de manipulación.
                Responde en formato JSON con análisis de seguridad.
                """,
                "user_prompt": """
                Supervisa la seguridad de estos datos:
                
                Datos: {input_data}
                
                Analiza:
                1. Anomalías en patrones de datos
                2. Valores extremos sospechosos
                3. Consistencia temporal
                4. Indicadores de manipulación
                
                Responde en JSON con: {{"security_status": "safe/suspicious/dangerous", "anomalies": [], "risk_score": 0.0, "recommendations": []}}
                """
            },
            
            # === BUSINESS AGENTS ===
            "financial_agent": {
                "system_prompt": """
                Eres un analista financiero experto en evaluación de riesgo crediticio para PYMEs.
                Analizas estados financieros, ratios y tendencias para determinar la salud financiera.
                Responde en formato JSON con análisis detallado y scoring.
                """,
                "user_prompt": """
                Realiza un análisis financiero completo de:
                
                Datos Financieros: {input_data}
                
                Analiza:
                1. Ratios de liquidez y solvencia
                2. Rentabilidad y eficiencia
                3. Estructura de capital
                4. Tendencias y estabilidad
                5. Capacidad de pago
                
                Responde en JSON con: {{"financial_score": 0.0, "liquidity_ratio": 0.0, "debt_ratio": 0.0, "profitability_score": 0.0, "analysis": "", "risk_factors": [], "confidence": 0.0}}
                """
            },
            
            "reputational_agent": {
                "system_prompt": """
                Eres un analista de reputación que evalúa la imagen pública y credibilidad de empresas.
                Analizas presencia digital, referencias comerciales y percepción del mercado.
                Responde en formato JSON con análisis reputacional.
                """,
                "user_prompt": """
                Evalúa la reputación de:
                
                Datos de Empresa: {input_data}
                
                Analiza:
                1. Presencia y reputación online
                2. Referencias comerciales
                3. Historial de cumplimiento
                4. Percepción en el sector
                5. Riesgos reputacionales
                
                Responde en JSON con: {{"reputation_score": 0.0, "online_presence": 0.0, "commercial_references": 0.0, "compliance_history": 0.0, "analysis": "", "risk_factors": [], "confidence": 0.0}}
                """
            },
            
            "behavioral_agent": {
                "system_prompt": """
                Eres un analista de comportamiento que evalúa patrones de pago y conducta comercial.
                Analizas historial de pagos, relaciones bancarias y comportamiento crediticio.
                Responde en formato JSON con análisis comportamental.
                """,
                "user_prompt": """
                Analiza el comportamiento crediticio de:
                
                Datos Comportamentales: {input_data}
                
                Evalúa:
                1. Historial de pagos
                2. Relaciones bancarias
                3. Patrones de endeudamiento
                4. Estabilidad comercial
                5. Predictores de comportamiento futuro
                
                Responde en JSON con: {{"behavioral_score": 0.0, "payment_history": 0.0, "banking_relationships": 0.0, "debt_patterns": 0.0, "analysis": "", "risk_factors": [], "confidence": 0.0}}
                """
            },
            
            # === INFRASTRUCTURE AGENTS ===
            "master_orchestrator": {
                "system_prompt": """
                Eres el coordinador maestro del sistema de evaluación de riesgo.
                Orquestas la ejecución de agentes y tomas decisiones sobre el flujo del proceso.
                Responde en formato JSON con decisiones de coordinación.
                """,
                "user_prompt": """
                Coordina la evaluación de riesgo para:
                
                Contexto: {input_data}
                Tarea: {task_type}
                
                Decide:
                1. Secuencia de agentes a ejecutar
                2. Prioridades y dependencias
                3. Criterios de éxito/fallo
                4. Estrategia de recuperación de errores
                
                Responde en JSON con: {{"execution_plan": [], "priorities": {{}}, "success_criteria": [], "error_handling": {{}}, "estimated_time": 0}}
                """
            },
            
            "scoring_agent": {
                "system_prompt": """
                Eres el agente consolidador que genera el scoring final de riesgo.
                Combinas resultados de múltiples agentes para producir un score 0-1000 y explicación.
                Responde en formato JSON con scoring detallado.
                """,
                "user_prompt": """
                Consolida los siguientes resultados para generar scoring final:
                
                Resultados de Agentes: {input_data}
                
                Genera:
                1. Score final (0-1000)
                2. Nivel de riesgo (alto/medio/bajo)
                3. Explicación detallada
                4. Factores contribuyentes
                5. Recomendación crediticia
                
                Responde en JSON con: {{"final_score": 0, "risk_level": "", "explanation": "", "contributing_factors": {{}}, "credit_recommendation": "", "confidence": 0.0}}
                """
            },
            
            "scenario_simulator": {
                "system_prompt": """
                Eres un simulador de escenarios que permite análisis "qué pasaría si".
                Modificas variables clave y predices el impacto en el scoring de riesgo.
                Responde en formato JSON con análisis de escenarios.
                """,
                "user_prompt": """
                Simula escenarios para:
                
                Datos Base: {input_data}
                Tipo de Simulación: {task_type}
                
                Simula:
                1. Escenarios optimista/pesimista/realista
                2. Impacto de cambios en variables clave
                3. Sensibilidad del scoring
                4. Viabilidad de escenarios
                
                Responde en JSON con: {{"scenarios": [], "sensitivity_analysis": {{}}, "impact_assessment": {{}}, "viability_scores": {{}}, "recommendations": []}}
                """
            }
        }
        
        # Return prompts for specific agent or default
        return agent_prompts.get(agent_id, {
            "system_prompt": "Eres un asistente especializado en análisis financiero. Responde en formato JSON.",
            "user_prompt": "Analiza los siguientes datos: {input_data}"
        })
    
    async def _save_agent_result(self, request: AgentRequest, response: AgentResponse):
        """Guarda el resultado del agente en la base de datos"""
        try:
            if self.sql_service:
                agent_result = AgentResult(
                    result_id=f"{response.agent_id}_{response.timestamp.strftime('%Y%m%d_%H%M%S')}",
                    evaluation_id=request.metadata.get("evaluation_id", "unknown") if request.metadata else "unknown",
                    agent_name=response.agent_id,
                    agent_type=response.agent_type.value,
                    result_data=json.dumps(response.result_data, ensure_ascii=False),
                    confidence_score=response.confidence_score,
                    processing_time_ms=response.processing_time_ms,
                    created_date=response.timestamp,
                    error_message=response.error_message
                )
                
                self.sql_service.save_agent_result(agent_result)
        except Exception as e:
            self.logger.warning(f"Failed to save agent result: {e}")
    
    # === CONVENIENCE METHODS FOR SPECIFIC AGENT TYPES ===
    
    async def execute_security_agent(self, agent_id: str, input_data: Dict[str, Any], 
                                   task_type: str = "security_check") -> AgentResponse:
        """Ejecuta un agente de seguridad"""
        request = AgentRequest(
            agent_id=agent_id,
            agent_type=AgentType.SECURITY,
            task_type=task_type,
            input_data=input_data,
            complexity=TaskComplexity.SIMPLE,  # Security checks are usually simple
            model_preference=ModelType.O3_MINI  # Use fast model for security
        )
        return await self.execute_agent(request)
    
    async def execute_business_agent(self, agent_id: str, input_data: Dict[str, Any], 
                                   task_type: str = "business_analysis") -> AgentResponse:
        """Ejecuta un agente de negocio"""
        request = AgentRequest(
            agent_id=agent_id,
            agent_type=AgentType.BUSINESS,
            task_type=task_type,
            input_data=input_data,
            complexity=TaskComplexity.COMPLEX,  # Business analysis is complex
            model_preference=ModelType.GPT4O  # Use powerful model for analysis
        )
        return await self.execute_agent(request)
    
    async def execute_infrastructure_agent(self, agent_id: str, input_data: Dict[str, Any], 
                                         task_type: str = "infrastructure_task") -> AgentResponse:
        """Ejecuta un agente de infraestructura"""
        complexity = TaskComplexity.COMPLEX if agent_id in ["scoring_agent", "scenario_simulator"] else TaskComplexity.MODERATE
        model = ModelType.GPT4O if complexity == TaskComplexity.COMPLEX else ModelType.AUTO
        
        request = AgentRequest(
            agent_id=agent_id,
            agent_type=AgentType.INFRASTRUCTURE,
            task_type=task_type,
            input_data=input_data,
            complexity=complexity,
            model_preference=model
        )
        return await self.execute_agent(request)
    
    # === WORKFLOW EXECUTION ===
    
    async def execute_full_risk_evaluation(self, company_data: Dict[str, Any], 
                                         evaluation_id: str = None) -> Dict[str, Any]:
        """Ejecuta el flujo completo de evaluación de riesgo"""
        
        if not evaluation_id:
            evaluation_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {
            "evaluation_id": evaluation_id,
            "company_data": company_data,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "final_result": None
        }
        
        try:
            # Phase 1: Security Validation
            self.logger.info(f"Starting security phase for {evaluation_id}")
            security_results = await self._execute_security_phase(company_data, evaluation_id)
            results["phases"]["security"] = security_results
            
            if not security_results["success"]:
                results["final_result"] = {"error": "Security validation failed", "details": security_results}
                return results
            
            # Phase 2: Business Analysis (Parallel)
            self.logger.info(f"Starting business phase for {evaluation_id}")
            business_results = await self._execute_business_phase(company_data, evaluation_id)
            results["phases"]["business"] = business_results
            
            # Phase 3: Infrastructure Processing
            self.logger.info(f"Starting infrastructure phase for {evaluation_id}")
            infrastructure_results = await self._execute_infrastructure_phase(business_results, evaluation_id)
            results["phases"]["infrastructure"] = infrastructure_results
            
            results["final_result"] = infrastructure_results.get("final_scoring", {})
            results["end_time"] = datetime.now().isoformat()
            
            self.logger.info(f"Risk evaluation completed for {evaluation_id}")
            return results
            
        except Exception as e:
            results["final_result"] = {"error": str(e)}
            results["end_time"] = datetime.now().isoformat()
            self.logger.error(f"Risk evaluation failed for {evaluation_id}: {e}")
            return results
    
    async def _execute_security_phase(self, company_data: Dict[str, Any], evaluation_id: str) -> Dict[str, Any]:
        """Ejecuta la fase de seguridad"""
        
        # Input validation
        validation_result = await self.execute_security_agent(
            "input_validator", 
            company_data, 
            "input_validation"
        )
        
        if not validation_result.success:
            return {"success": False, "error": "Input validation failed", "details": validation_result.result_data}
        
        # Security supervision
        security_result = await self.execute_security_agent(
            "security_supervisor", 
            company_data, 
            "security_check"
        )
        
        return {
            "success": True,
            "validation": validation_result.result_data,
            "security": security_result.result_data,
            "validated_data": validation_result.result_data.get("validated_data", company_data)
        }
    
    async def _execute_business_phase(self, company_data: Dict[str, Any], evaluation_id: str) -> Dict[str, Any]:
        """Ejecuta la fase de análisis de negocio en paralelo"""
        
        # Execute business agents in parallel
        tasks = [
            self.execute_business_agent("financial_agent", company_data, "financial_analysis"),
            self.execute_business_agent("reputational_agent", company_data, "reputational_analysis"),
            self.execute_business_agent("behavioral_agent", company_data, "behavioral_analysis")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "financial": results[0].result_data if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "reputational": results[1].result_data if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "behavioral": results[2].result_data if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "success": all(not isinstance(r, Exception) and r.success for r in results)
        }
    
    async def _execute_infrastructure_phase(self, business_results: Dict[str, Any], evaluation_id: str) -> Dict[str, Any]:
        """Ejecuta la fase de infraestructura"""
        
        # Scoring consolidation
        scoring_result = await self.execute_infrastructure_agent(
            "scoring_agent", 
            business_results, 
            "scoring_consolidation"
        )
        
        return {
            "final_scoring": scoring_result.result_data,
            "success": scoring_result.success
        }
    
    # === UTILITY METHODS ===
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso de modelos"""
        return {
            **self.model_stats,
            "cost_estimate": {
                "gpt4o_cost": self.model_stats["gpt4o_requests"] * 0.002,  # Estimate
                "o3mini_cost": self.model_stats["o3mini_requests"] * 0.0001,  # Estimate
                "total_estimated": (self.model_stats["gpt4o_requests"] * 0.002) + (self.model_stats["o3mini_requests"] * 0.0001)
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Verifica el estado de salud del conector"""
        return {
            "status": "healthy" if self.openai_service else "unhealthy",
            "services": {
                "openai": self.openai_service is not None,
                "sql": self.sql_service is not None,
                "blob": self.blob_service is not None,
                "semantic_kernel": self.semantic_kernel_service is not None
            },
            "model_stats": self.get_model_stats(),
            "last_check": datetime.now().isoformat()
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión con ambos modelos"""
        test_results = {
            "gpt4o": {"status": "unknown"},
            "o3mini": {"status": "unknown"},
            "overall": "unknown"
        }
        
        try:
            # Test GPT-4o
            gpt4o_response = await self.execute_with_model(
                prompt="Test connection",
                system_prompt="Respond with 'Connection successful'",
                model_type=ModelType.GPT4O,
                max_tokens=50,
                agent_id="connection_test"
            )
            test_results["gpt4o"] = {
                "status": "success",
                "tokens": gpt4o_response.tokens_used,
                "response": gpt4o_response.response_text[:50]
            }
        except Exception as e:
            test_results["gpt4o"] = {"status": "failed", "error": str(e)}
        
        try:
            # Test o3-mini
            o3mini_response = await self.execute_with_model(
                prompt="Test connection",
                system_prompt="Respond with 'Connection successful'",
                model_type=ModelType.O3_MINI,
                max_tokens=50,
                agent_id="connection_test"
            )
            test_results["o3mini"] = {
                "status": "success",
                "tokens": o3mini_response.tokens_used,
                "response": o3mini_response.response_text[:50]
            }
        except Exception as e:
            test_results["o3mini"] = {"status": "failed", "error": str(e)}
        
        # Overall status
        both_success = (test_results["gpt4o"]["status"] == "success" and 
                       test_results["o3mini"]["status"] == "success")
        test_results["overall"] = "success" if both_success else "partial" if any(
            test_results[model]["status"] == "success" for model in ["gpt4o", "o3mini"]
        ) else "failed"
        
        return test_results


# === GLOBAL CONNECTOR INSTANCE ===

_global_connector: Optional[AgentConnector] = None

def get_agent_connector() -> AgentConnector:
    """Obtiene la instancia global del conector de agentes"""
    global _global_connector
    
    if _global_connector is None:
        _global_connector = AgentConnector()
    
    return _global_connector

async def initialize_agent_connector() -> bool:
    """Inicializa el conector global de agentes"""
    connector = get_agent_connector()
    return await connector.initialize()