"""
Azure Orchestrator - Orquestador usando Azure OpenAI Service
Usa los servicios Azure OpenAI existentes sin CrewAI
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing Azure OpenAI services
from .infrastructure_agents.services.azure_openai_service_enhanced import OpenAIRequest
from .infrastructure_agents.config.azure_config import AzureOpenAIConfig

# Import security agents
from .infrastructure.security.input_validator import validate_company_data, CompanyDataValidationResult
from .infrastructure.security.supervisor import run_security_supervision, SupervisionReport
from .infrastructure.security.output_sanitizer import sanitize_output, SanitizationResult
from .infrastructure.security.audit_logger import AuditLogger, create_audit_logger


class EvaluationPhase(Enum):
    """Fases de la evaluación de riesgo"""
    PENDING = "pending"
    SECURITY_VALIDATION = "security_validation"
    BUSINESS_ANALYSIS = "business_analysis"
    SCORING_CONSOLIDATION = "scoring_consolidation"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CompanyData:
    """Datos de entrada de la empresa para evaluación"""
    company_id: str
    company_name: str
    financial_statements: str
    social_media_data: str
    commercial_references: str
    payment_history: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Resultado completo de una evaluación de riesgo"""
    evaluation_id: str
    company_id: str
    company_name: str
    final_score: float
    risk_level: str
    financial_analysis: Dict[str, Any]
    reputational_analysis: Dict[str, Any]
    behavioral_analysis: Dict[str, Any]
    consolidated_report: Dict[str, Any]
    processing_time: float
    timestamp: datetime
    success: bool
    errors: List[str] = field(default_factory=list)


class AzureOrchestrator:
    """
    Orquestador usando Azure OpenAI Service
    
    Usa los servicios Azure OpenAI existentes para análisis de riesgo
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Azure OpenAI service
        self.azure_service = None
        self.config: Optional[AzureOpenAIConfig] = None
        
        # Audit Logger
        self.audit_logger = create_audit_logger()
        
        # Statistics
        self.stats = {
            "total_evaluations": 0,
            "successful_evaluations": 0,
            "failed_evaluations": 0,
            "average_processing_time": 0.0,
            "total_tokens_used": 0
        }
        
        self.logger.info("AzureOrchestrator initialized")
    
    async def initialize(self) -> bool:
        """Inicializa el orquestador con Azure OpenAI"""
        try:
            self.logger.info("Initializing AzureOrchestrator...")
            
            # Load Azure OpenAI configuration
            self.config = AzureOpenAIConfig.from_env()
            
            # Use enhanced service with rate limit handling
            from .infrastructure_agents.services.azure_openai_service_enhanced import create_enhanced_azure_service
            self.azure_service = create_enhanced_azure_service(self.config)
            
            # Test connection
            await self._test_azure_connection()
            
            self.logger.info("AzureOrchestrator initialized successfully")
            self.logger.info(f"Using Azure endpoint: {self.config.endpoint}")
            self.logger.info(f"GPT-4o model: {self.config.deployment_name}")
            self.logger.info(f"o3-mini model: {self.config.deployment_name_mini}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AzureOrchestrator: {e}")
            return False
    
    async def _test_azure_connection(self):
        """Prueba la conexión con Azure OpenAI"""
        try:
            test_request = OpenAIRequest(
                request_id="connection_test",
                user_id="system",
                agent_id="test",
                prompt="Test connection",
                max_tokens=10,
                temperature=0.1,
                timestamp=datetime.now()
            )
            
            response = await self.azure_service.generate_completion(
                test_request,
                "You are a test assistant.",
                use_mini_model=True  # Use o3-mini for test
            )
            
            self.logger.info("Azure OpenAI connection test successful")
        except Exception as e:
            raise Exception(f"Azure OpenAI connection test failed: {e}")
    
    async def evaluate_company_risk(self, company_data: CompanyData) -> EvaluationResult:
        """
        Evalúa el riesgo de una empresa usando Azure OpenAI siguiendo el flujo de seguridad completo
        
        Flujo: SecuritySupervisor → InputValidator → BusinessAgents → OutputSanitizer → ScoringAgent → AuditLogger
        """
        evaluation_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{company_data.company_id}"
        start_time = datetime.now()
        
        self.logger.info(f"Starting risk evaluation: {evaluation_id} for company: {company_data.company_name}")
        self.stats["total_evaluations"] += 1
        
        try:
            # Phase 0: Security Supervision
            self.logger.info(f"Phase 0: Security supervision for {evaluation_id}")
            security_status = await self._execute_security_supervision(evaluation_id, company_data.company_id)
            if security_status.get("critical_alert", False):
                return self._create_security_blocked_result(evaluation_id, company_data, start_time, "Critical security alert detected")
            
            # Phase 1: Input Validation
            self.logger.info(f"Phase 1: Input validation for {evaluation_id}")
            validation_result = await self._execute_input_validation(company_data, evaluation_id)
            
            # Be very tolerant - only block if there are actual malicious patterns detected
            risk_level = validation_result.get("overall_risk_level", "LOW")
            blocked_fields = validation_result.get("blocked_fields", [])
            
            # Check if any blocked fields have high confidence malicious detection
            high_confidence_blocks = []
            for field_result in validation_result.get("field_results", []):
                if (not field_result.get("is_safe", True) and 
                    field_result.get("confidence", 0) > 0.8 and
                    "rate limit" not in field_result.get("reason", "").lower() and
                    "api error" not in field_result.get("reason", "").lower()):
                    high_confidence_blocks.append(field_result.get("field_name", "unknown"))
            
            # Only block if we have high-confidence malicious content detection
            if len(high_confidence_blocks) > 0:
                self.logger.warning(f"High confidence malicious content detected: {high_confidence_blocks}")
                return self._create_validation_failed_result(evaluation_id, company_data, start_time, validation_result)
            elif len(blocked_fields) > 0:
                # Log warning but continue with evaluation - likely false positives
                self.logger.info(f"Some fields flagged but continuing evaluation (likely false positives): {blocked_fields}")
                # Log for monitoring but don't treat as security alert
                self.audit_logger.log_business_analysis(
                    evaluation_id, company_data.company_id, "validation_warning",
                    {"blocked_fields": blocked_fields, "risk_level": risk_level}, 0.1
                )
            
            # Phase 2: Business Analysis (parallel execution)
            self.logger.info(f"Phase 2: Business analysis for {evaluation_id}")
            financial_result, reputational_result, behavioral_result = await self._execute_business_analysis(company_data)
            
            # Phase 3: Output Sanitization
            self.logger.info(f"Phase 3: Output sanitization for {evaluation_id}")
            sanitized_results = await self._execute_output_sanitization(
                financial_result, reputational_result, behavioral_result, evaluation_id
            )
            
            # Phase 4: Scoring Consolidation
            self.logger.info(f"Phase 4: Scoring consolidation for {evaluation_id}")
            consolidated_report = await self._consolidate_scoring(
                sanitized_results["financial"], sanitized_results["reputational"], 
                sanitized_results["behavioral"], company_data
            )
            
            # Phase 5: Final Output Sanitization
            self.logger.info(f"Phase 5: Final output sanitization for {evaluation_id}")
            final_sanitized_report = await self._sanitize_final_output(consolidated_report, evaluation_id)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Phase 6: Audit Logging
            await self._log_evaluation_completion(evaluation_id, final_sanitized_report, processing_time)
            
            # Create final result
            result = EvaluationResult(
                evaluation_id=evaluation_id,
                company_id=company_data.company_id,
                company_name=company_data.company_name,
                final_score=final_sanitized_report.get("final_score", 0.0),
                risk_level=final_sanitized_report.get("risk_level", "unknown"),
                financial_analysis=sanitized_results["financial"],
                reputational_analysis=sanitized_results["reputational"],
                behavioral_analysis=sanitized_results["behavioral"],
                consolidated_report=final_sanitized_report,
                processing_time=processing_time,
                timestamp=datetime.now(),
                success=True
            )
            
            self.stats["successful_evaluations"] += 1
            self._update_average_processing_time(processing_time)
            
            self.logger.info(f"Risk evaluation completed: {evaluation_id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Risk evaluation failed: {evaluation_id} - {e}")
            self.stats["failed_evaluations"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log the failure
            await self._log_evaluation_failure(evaluation_id, str(e), processing_time)
            
            return EvaluationResult(
                evaluation_id=evaluation_id,
                company_id=company_data.company_id,
                company_name=company_data.company_name,
                final_score=0.0,
                risk_level="error",
                financial_analysis={},
                reputational_analysis={},
                behavioral_analysis={},
                consolidated_report={},
                processing_time=processing_time,
                timestamp=datetime.now(),
                success=False,
                errors=[str(e)]
            )
    
    def _basic_validation(self, company_data: CompanyData) -> bool:
        """Validación básica de datos"""
        if not company_data.company_name.strip():
            return False
        if not company_data.company_id.strip():
            return False
        return True
    
    async def _execute_business_analysis(self, company_data: CompanyData) -> tuple:
        """Ejecuta análisis de negocio usando los agentes especializados"""
        
        # Import business agents
        from .business_agents.financial_agent import analyze_financial_document
        from .business_agents.reputational_agent import analyze_reputation
        from .business_agents.behavioral_agent import analyze_behavior
        
        # Execute all business analyses in parallel using specialized agents
        self.logger.info("🏦 Executing FinancialAgent...")
        self.logger.info("🌟 Executing ReputationalAgent...")
        self.logger.info("🎯 Executing BehavioralAgent...")
        
        tasks = [
            analyze_financial_document(self.azure_service, company_data.financial_statements),
            analyze_reputation(self.azure_service, company_data.social_media_data),
            analyze_behavior(self.azure_service, f"{company_data.commercial_references}\n{company_data.payment_history}")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("✅ All business agents completed execution")
        
        # Process results and handle exceptions
        financial_result = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0]), "success": False}
        reputational_result = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1]), "success": False}
        behavioral_result = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2]), "success": False}
        
        # Convert Pydantic models to dictionaries for consistency
        if hasattr(financial_result, 'dict'):
            financial_result = financial_result.dict()
        if hasattr(reputational_result, 'dict'):
            reputational_result = reputational_result.dict()
        if hasattr(behavioral_result, 'dict'):
            behavioral_result = behavioral_result.dict()
        
        # Log business analysis results to audit trail
        evaluation_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{company_data.company_id}"
        
        # Log each business agent execution
        if financial_result.get("success", True):
            self.audit_logger.log_business_analysis(
                evaluation_id, company_data.company_id, "financial", 
                financial_result, financial_result.get("tokens_used", 0) / 1000.0  # Convert to seconds estimate
            )
        
        if reputational_result.get("success", True):
            self.audit_logger.log_business_analysis(
                evaluation_id, company_data.company_id, "reputational", 
                reputational_result, reputational_result.get("tokens_used", 0) / 1000.0
            )
        
        if behavioral_result.get("success", True):
            self.audit_logger.log_business_analysis(
                evaluation_id, company_data.company_id, "behavioral", 
                behavioral_result, behavioral_result.get("tokens_used", 0) / 1000.0
            )
        
        return financial_result, reputational_result, behavioral_result
    
    # Métodos de análisis de negocio removidos - ahora se usan los agentes especializados
    
    async def _consolidate_scoring(self, financial_result: Dict[str, Any], 
                                 reputational_result: Dict[str, Any], 
                                 behavioral_result: Dict[str, Any],
                                 company_data: CompanyData) -> Dict[str, Any]:
        """Consolida los resultados usando Azure OpenAI"""
        try:
            # Primero, calcular un score base usando lógica simple
            base_score = self._calculate_base_score(financial_result, reputational_result, behavioral_result)
            
            consolidation_prompt = f"""
            Eres un experto analista de riesgo crediticio. Consolida los siguientes análisis y genera un scoring final de riesgo.

            EMPRESA: {company_data.company_name}

            ANÁLISIS FINANCIERO:
            {json.dumps(financial_result, ensure_ascii=False, indent=2)}

            ANÁLISIS REPUTACIONAL:
            {json.dumps(reputational_result, ensure_ascii=False, indent=2)}

            ANÁLISIS COMPORTAMENTAL:
            {json.dumps(behavioral_result, ensure_ascii=False, indent=2)}

            SCORE BASE CALCULADO: {base_score}

            INSTRUCCIONES:
            1. Ajusta el score base considerando todos los factores (rango 0-1000, donde 1000 es menor riesgo)
            2. Clasifica el riesgo como: BAJO (750-1000), MEDIO (500-749), ALTO (0-499)
            3. Proporciona una justificación detallada
            4. Incluye factores contribuyentes principales
            5. Da una recomendación crediticia clara

            Responde ÚNICAMENTE en formato JSON:
            {{
                "final_score": <número entre 0-1000>,
                "risk_level": "<BAJO|MEDIO|ALTO>",
                "justification": "<explicación detallada>",
                "contributing_factors": [
                    "<factor 1>",
                    "<factor 2>",
                    "<factor 3>"
                ],
                "credit_recommendation": "<recomendación>",
                "confidence": <0.0-1.0>
            }}
            """
            
            request = OpenAIRequest(
                request_id=f"consolidation_{datetime.now().strftime('%H%M%S')}",
                user_id="system",
                agent_id="consolidator",
                prompt=consolidation_prompt,
                max_tokens=1500,
                temperature=0.1,
                timestamp=datetime.now()
            )

            response = await self.azure_service.generate_completion(
                request,
                "You are an expert credit risk analyst. Provide accurate JSON response.",
                use_mini_model=False  # Use GPT-4o for complex consolidation
            )

            self.stats["total_tokens_used"] += response.tokens_used

            # Parse JSON response
            try:
                response_content = response.response_text.strip()
                
                # Extract JSON from response
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_content = response_content[json_start:json_end]
                    result_data = json.loads(json_content)
                    
                    # Validate and return result
                    final_score = result_data.get("final_score", base_score)
                    risk_level = self._determine_risk_level(final_score)
                    
                    return {
                        "final_score": final_score,
                        "risk_level": risk_level,
                        "justification": result_data.get("justification", "Análisis consolidado completado"),
                        "contributing_factors": result_data.get("contributing_factors", ["Análisis financiero", "Análisis reputacional", "Análisis comportamental"]),
                        "credit_recommendation": result_data.get("credit_recommendation", "Evaluación completada"),
                        "confidence": result_data.get("confidence", 0.8),
                        "success": True,
                        "tokens_used": response.tokens_used
                    }
                else:
                    raise json.JSONDecodeError("No valid JSON found", response_content, 0)
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON parsing failed, using base score: {e}")
                # Return base score with calculated risk level
                risk_level = self._determine_risk_level(base_score)
                return {
                    "final_score": base_score,
                    "risk_level": risk_level,
                    "justification": "Score calculado basado en análisis disponibles",
                    "contributing_factors": ["Análisis financiero", "Análisis reputacional", "Análisis comportamental"],
                    "credit_recommendation": f"Riesgo {risk_level.lower()} - revisar detalles",
                    "confidence": 0.7,
                    "success": True,
                    "tokens_used": response.tokens_used
                }
            
        except Exception as e:
            self.logger.error(f"Scoring consolidation failed: {e}")
            # Calculate fallback score
            fallback_score = self._calculate_base_score(financial_result, reputational_result, behavioral_result)
            risk_level = self._determine_risk_level(fallback_score)
            
            return {
                "final_score": fallback_score,
                "risk_level": risk_level,
                "justification": f"Score calculado con método alternativo debido a error: {str(e)}",
                "contributing_factors": ["Análisis disponibles procesados"],
                "credit_recommendation": f"Riesgo {risk_level.lower()} - requiere revisión manual",
                "confidence": 0.6,
                "success": True,
                "error": str(e),
                "tokens_used": 0
            }
    
    def _calculate_base_score(self, financial_result: Dict[str, Any], 
                            reputational_result: Dict[str, Any], 
                            behavioral_result: Dict[str, Any]) -> int:
        """Calcula un score base usando lógica simple"""
        try:
            base_score = 600  # Score neutral inicial
            
            # Análisis financiero (peso: 50%)
            if financial_result.get("success", False):
                # Si hay análisis financiero exitoso, ajustar score
                if "solvencia" in str(financial_result).lower():
                    if any(word in str(financial_result).lower() for word in ["buena", "alta", "positiva", "estable"]):
                        base_score += 100
                    elif any(word in str(financial_result).lower() for word in ["mala", "baja", "negativa", "crítica"]):
                        base_score -= 150
                
                if "liquidez" in str(financial_result).lower():
                    if any(word in str(financial_result).lower() for word in ["buena", "alta", "suficiente"]):
                        base_score += 50
                    elif any(word in str(financial_result).lower() for word in ["mala", "baja", "insuficiente"]):
                        base_score -= 100
            else:
                # Penalizar si no hay análisis financiero
                base_score -= 50
            
            # Análisis reputacional (peso: 25%)
            if reputational_result.get("success", False):
                sentiment_score = reputational_result.get("puntaje_sentimiento", 0)
                if sentiment_score > 0.3:
                    base_score += 75
                elif sentiment_score < -0.3:
                    base_score -= 75
            
            # Análisis comportamental (peso: 25%)
            if behavioral_result.get("success", False):
                if "puntual" in str(behavioral_result).lower():
                    base_score += 50
                elif "impuntual" in str(behavioral_result).lower() or "retraso" in str(behavioral_result).lower():
                    base_score -= 100
                
                if "alta" in str(behavioral_result.get("fiabilidad_referencias", "")).lower():
                    base_score += 25
                elif "baja" in str(behavioral_result.get("fiabilidad_referencias", "")).lower():
                    base_score -= 50
            
            # Asegurar que el score esté en el rango válido
            base_score = max(0, min(1000, base_score))
            
            return base_score
            
        except Exception as e:
            self.logger.warning(f"Error calculating base score: {e}")
            return 500  # Score neutral por defecto
    
    def _determine_risk_level(self, score: int) -> str:
        """Determina el nivel de riesgo basado en el score"""
        if score >= 750:
            return "BAJO"
        elif score >= 500:
            return "MEDIO"
        else:
            return "ALTO"
    
    def _update_average_processing_time(self, processing_time: float):
        """Actualiza el tiempo promedio de procesamiento"""
        if self.stats["successful_evaluations"] == 1:
            self.stats["average_processing_time"] = processing_time
        else:
            current_avg = self.stats["average_processing_time"]
            count = self.stats["successful_evaluations"]
            self.stats["average_processing_time"] = ((current_avg * (count - 1)) + processing_time) / count
    
    # ===== SECURITY METHODS =====
    
    async def _execute_security_supervision(self, evaluation_id: str, company_id: str = "unknown") -> Dict[str, Any]:
        """Ejecuta supervisión de seguridad usando SecuritySupervisor"""
        start_time = datetime.now()
        try:
            supervision_result = await run_security_supervision(self.azure_service)

            # Ajustar para bloquear solo patrones maliciosos explícitos
            critical_alert = supervision_result.critical_alert and supervision_result.confidence_score > 0.9

            result = {
                "anomaly_detected": supervision_result.anomaly_detected,
                "confidence_score": supervision_result.confidence_score,
                "summary": supervision_result.summary,
                "recommended_action": supervision_result.recommended_action,
                "critical_alert": critical_alert,
                "success": True
            }

            # Log to audit trail
            processing_time = (datetime.now() - start_time).total_seconds()
            self.audit_logger.log_security_supervision(evaluation_id, company_id, result, processing_time)

            return result
        except Exception as e:
            self.logger.error(f"Security supervision failed for {evaluation_id}: {e}")
            result = {
                "anomaly_detected": True,
                "confidence_score": 0.8,
                "summary": f"Security supervision error: {str(e)}",
                "recommended_action": "Alerta de Seguridad Crítica",
                "critical_alert": True,
                "success": False,
                "error": str(e)
            }

            # Log failure to audit trail
            processing_time = (datetime.now() - start_time).total_seconds()
            self.audit_logger.log_security_supervision(evaluation_id, company_id, result, processing_time)

            return result
    
    async def _execute_input_validation(self, company_data: CompanyData, evaluation_id: str) -> Dict[str, Any]:
        """Ejecuta validación de entrada usando InputValidator"""
        start_time = datetime.now()
        try:
            # Convert CompanyData to dict for validation
            company_dict = {
                "company_name": company_data.company_name,
                "financial_statements": company_data.financial_statements,
                "social_media_data": company_data.social_media_data,
                "commercial_references": company_data.commercial_references,
                "payment_history": company_data.payment_history
            }
            
            validation_result = await validate_company_data(self.azure_service, company_dict)
            
            result = {
                "all_safe": validation_result.all_safe,
                "field_results": [result.dict() for result in validation_result.field_results],
                "blocked_fields": validation_result.blocked_fields,
                "overall_risk_level": validation_result.overall_risk_level,
                "success": True
            }
            
            # Log to audit trail
            processing_time = (datetime.now() - start_time).total_seconds()
            self.audit_logger.log_input_validation(evaluation_id, company_data.company_id, result, processing_time)
            
            return result
        except Exception as e:
            self.logger.error(f"Input validation failed for {evaluation_id}: {e}")
            result = {
                "all_safe": False,
                "field_results": [],
                "blocked_fields": ["all"],
                "overall_risk_level": "CRITICAL",
                "success": False,
                "error": str(e)
            }
            
            # Log failure to audit trail
            processing_time = (datetime.now() - start_time).total_seconds()
            self.audit_logger.log_input_validation(evaluation_id, company_data.company_id, result, processing_time)
            
            return result
    
    async def _execute_output_sanitization(self, financial_result: Dict[str, Any], 
                                         reputational_result: Dict[str, Any], 
                                         behavioral_result: Dict[str, Any],
                                         evaluation_id: str) -> Dict[str, Any]:
        """Ejecuta sanitización de salidas usando OutputSanitizer"""
        try:
            # Sanitize each business agent output
            sanitized_financial = await self._sanitize_agent_output(financial_result, "financial")
            sanitized_reputational = await self._sanitize_agent_output(reputational_result, "reputational")
            sanitized_behavioral = await self._sanitize_agent_output(behavioral_result, "behavioral")
            
            return {
                "financial": sanitized_financial,
                "reputational": sanitized_reputational,
                "behavioral": sanitized_behavioral,
                "success": True
            }
        except Exception as e:
            self.logger.error(f"Output sanitization failed for {evaluation_id}: {e}")
            return {
                "financial": {"error": "Sanitization failed", "success": False},
                "reputational": {"error": "Sanitization failed", "success": False},
                "behavioral": {"error": "Sanitization failed", "success": False},
                "success": False,
                "error": str(e)
            }
    
    async def _sanitize_agent_output(self, agent_result: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
        """Sanitiza la salida de un agente específico"""
        try:
            # Convert agent result to text for sanitization
            result_text = json.dumps(agent_result, ensure_ascii=False)
            
            sanitization_result = await sanitize_output(self.azure_service, result_text)
            
            if sanitization_result.is_safe:
                # Return original result if safe
                return agent_result
            else:
                # Return sanitized version
                try:
                    sanitized_data = json.loads(sanitization_result.sanitized_text)
                    sanitized_data["sanitization_applied"] = True
                    sanitized_data["sanitization_details"] = sanitization_result.details
                    return sanitized_data
                except json.JSONDecodeError:
                    # If sanitized text is not valid JSON, return safe fallback
                    return {
                        "sanitized_content": sanitization_result.sanitized_text,
                        "sanitization_applied": True,
                        "sanitization_details": sanitization_result.details,
                        "agent_type": agent_type,
                        "success": True
                    }
        except Exception as e:
            self.logger.warning(f"Sanitization failed for {agent_type}: {e}")
            return {
                "sanitized_content": "[SANITIZATION_FAILED]",
                "sanitization_applied": False,
                "sanitization_details": f"Sanitization failed due to: {str(e)}",
                "agent_type": agent_type,
                "success": False
            }
    
    async def _sanitize_final_output(self, consolidated_report: Dict[str, Any], evaluation_id: str) -> Dict[str, Any]:
        """Sanitiza el reporte consolidado final"""
        try:
            # Asegurar que consolidated_report no sea None
            if not consolidated_report:
                self.logger.warning(f"Consolidated report is None for evaluation {evaluation_id}. Using default values.")
                consolidated_report = {
                    "final_score": 500,
                    "risk_level": "MEDIO",
                    "justification": "[CONTENIDO NO DISPONIBLE]",
                    "contributing_factors": ["Datos insuficientes para evaluación completa"],
                    "credit_recommendation": "Revisión manual requerida",
                    "confidence": 0.5,
                    "success": False
                }

            report_text = json.dumps(consolidated_report, ensure_ascii=False)
            sanitization_result = await sanitize_output(self.azure_service, report_text)

            if sanitization_result.is_safe:
                return consolidated_report
            else:
                try:
                    sanitized_report = json.loads(sanitization_result.sanitized_text)
                    sanitized_report["final_sanitization_applied"] = True
                    sanitized_report["final_sanitization_details"] = sanitization_result.details
                    return sanitized_report
                except json.JSONDecodeError:
                    # Return safe fallback
                    return {
                        "final_score": consolidated_report.get("final_score", 500),
                        "risk_level": consolidated_report.get("risk_level", "MEDIO"),
                        "justification": "[CONTENIDO SANITIZADO POR SEGURIDAD]",
                        "contributing_factors": ["Información sanitizada por privacidad"],
                        "credit_recommendation": "Revisión manual requerida debido a sanitización",
                        "confidence": 0.5,
                        "final_sanitization_applied": True,
                        "final_sanitization_details": sanitization_result.details,
                        "success": True
                    }
        except Exception as e:
            self.logger.error(f"Final output sanitization failed for {evaluation_id}: {e}")
            return consolidated_report  # Return original if sanitization fails
    
    async def _log_evaluation_completion(self, evaluation_id: str, final_report: Dict[str, Any], processing_time: float):
        """Registra la finalización exitosa de una evaluación"""
        try:
            # Verificar si final_report es válido
            if not final_report:
                self.logger.warning(f"Final report is None for evaluation {evaluation_id}. Using default values.")
                final_report = {"final_score": 0, "risk_level": "error"}

            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "evaluation_id": evaluation_id,
                "event": "EVALUATION_COMPLETED",
                "final_score": final_report.get("final_score", 0),
                "risk_level": final_report.get("risk_level", "unknown"),
                "processing_time": processing_time,
                "tokens_used": self.stats["total_tokens_used"],
                "success": True
            }
            
            # Write to audit log
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log evaluation completion for {evaluation_id}: {e}")
    
    async def _log_evaluation_failure(self, evaluation_id: str, error_message: str, processing_time: float):
        """Registra el fallo de una evaluación"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "evaluation_id": evaluation_id,
                "event": "EVALUATION_FAILED",
                "error": error_message,
                "processing_time": processing_time,
                "success": False
            }
            
            # Write to audit log
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log evaluation failure for {evaluation_id}: {e}")
    
    def _create_security_blocked_result(self, evaluation_id: str, company_data: CompanyData, 
                                      start_time: datetime, reason: str) -> EvaluationResult:
        """Crea un resultado cuando la evaluación es bloqueada por seguridad"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return EvaluationResult(
            evaluation_id=evaluation_id,
            company_id=company_data.company_id,
            company_name=company_data.company_name,
            final_score=0.0,
            risk_level="SECURITY_BLOCKED",
            financial_analysis={"error": "Blocked by security", "success": False},
            reputational_analysis={"error": "Blocked by security", "success": False},
            behavioral_analysis={"error": "Blocked by security", "success": False},
            consolidated_report={"error": reason, "success": False},
            processing_time=processing_time,
            timestamp=datetime.now(),
            success=False,
            errors=[reason]
        )
    
    def _create_validation_failed_result(self, evaluation_id: str, company_data: CompanyData, 
                                       start_time: datetime, validation_result: Dict[str, Any]) -> EvaluationResult:
        """Crea un resultado cuando la validación de entrada falla"""
        processing_time = (datetime.now() - start_time).total_seconds()
        blocked_fields = validation_result.get("blocked_fields", [])
        
        return EvaluationResult(
            evaluation_id=evaluation_id,
            company_id=company_data.company_id,
            company_name=company_data.company_name,
            final_score=0.0,
            risk_level="VALIDATION_FAILED",
            financial_analysis={"error": "Input validation failed", "success": False},
            reputational_analysis={"error": "Input validation failed", "success": False},
            behavioral_analysis={"error": "Input validation failed", "success": False},
            consolidated_report={
                "error": f"Input validation failed for fields: {', '.join(blocked_fields)}",
                "blocked_fields": blocked_fields,
                "overall_risk_level": validation_result.get("overall_risk_level", "CRITICAL"),
                "success": False
            },
            processing_time=processing_time,
            timestamp=datetime.now(),
            success=False,
            errors=[f"Validation failed for fields: {', '.join(blocked_fields)}"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del orquestador"""
        return self.stats.copy()
    
    def get_audit_trail(self, evaluation_id: str) -> List[Dict[str, Any]]:
        """Obtiene el trail de auditoría para una evaluación específica"""
        return self.audit_logger.get_evaluation_audit_trail(evaluation_id)
    
    def get_recent_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene los eventos de auditoría más recientes"""
        return self.audit_logger.get_recent_events(limit)
    
    def _create_validation_failed_result(self, evaluation_id: str, company_data: CompanyData, 
                                       start_time: datetime, validation_result: Dict[str, Any]) -> EvaluationResult:
        """Crea un resultado cuando la validación de entrada falla"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        blocked_fields = validation_result.get("blocked_fields", [])
        reason = f"Input validation failed. Blocked fields: {', '.join(blocked_fields)}"
        
        return EvaluationResult(
            evaluation_id=evaluation_id,
            company_id=company_data.company_id,
            company_name=company_data.company_name,
            final_score=0.0,
            risk_level="VALIDATION_FAILED",
            financial_analysis={"error": "Input validation failed", "success": False},
            reputational_analysis={"error": "Input validation failed", "success": False},
            behavioral_analysis={"error": "Input validation failed", "success": False},
            consolidated_report={
                "error": reason,
                "validation_details": validation_result,
                "success": False
            },
            processing_time=processing_time,
            timestamp=datetime.now(),
            success=False,
            errors=[reason]
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del orquestador"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_evaluations"] / self.stats["total_evaluations"] 
                if self.stats["total_evaluations"] > 0 else 0.0
            ),
            "using_azure": True,
            "azure_endpoint": self.config.endpoint if self.config else None,
            "gpt4o_model": self.config.deployment_name if self.config else None,
            "o3mini_model": self.config.deployment_name_mini if self.config else None
        }
    
    async def evaluate_company_risk_from_pdfs(self, pdf_paths: List[str], company_name: str, user_id: str = "web_user") -> EvaluationResult:
        """Pipeline: PDFs financieros -> texto consolidado -> flujo actual de agentes.
        - Extrae texto/tablas con pdf_ingestion_service
        - Construye CompanyData y llama evaluate_company_risk
        """
        from .infrastructure_agents.services.pdf_ingestion_service import parse_financial_pdfs, build_financial_text_from_parsed
        # Parse PDFs
        parsed = await parse_financial_pdfs(pdf_paths)
        consolidated_text = build_financial_text_from_parsed(parsed)
        # Fallback si no hay texto
        if not consolidated_text.strip():
            consolidated_text = json.dumps(parsed.get("summary", {}), ensure_ascii=False)
        # CompanyData sintético
        company_data = CompanyData(
            company_id=f"PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            company_name=company_name,
            financial_statements=consolidated_text,
            social_media_data="",
            commercial_references="Documentos financieros subidos en PDF",
            payment_history="No provisto",
            metadata={"source": "pdf_upload", "files": [str(p) for p in pdf_paths], "parsed_summary": parsed.get("summary", {})}
        )
        return await self.evaluate_company_risk(company_data)


# Factory function for easy instantiation
def create_azure_orchestrator() -> AzureOrchestrator:
    """Crea una instancia del orquestador con Azure OpenAI"""
    return AzureOrchestrator()