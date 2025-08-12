"""
Infrastructure Service
Servicio principal que integra todos los servicios Azure para agentes de infraestructura
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .config.azure_config import AzureInfrastructureConfig
from .services.azure_ai_service import AzureAIAgentService
from .services.azure_openai_service import AzureOpenAIService, SecurityProxyConfig
from .services.azure_sql_service import AzureSQLService
from .services.azure_blob_service import AzureBlobService
from .services.semantic_kernel_service import SemanticKernelService


@dataclass
class InfrastructureStatus:
    """Estado de la infraestructura"""
    overall_status: str
    services_status: Dict[str, Dict[str, Any]]
    last_check: datetime
    error_count: int
    warnings: List[str]


class InfrastructureService:
    """
    Servicio principal de infraestructura que coordina todos los servicios Azure
    Proporciona una interfaz unificada para los agentes de infraestructura
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = AzureInfrastructureConfig()
        
        # Validate configuration
        config_errors = self.config.validate_config()
        if config_errors:
            error_msg = f"Configuration errors: {', '.join(config_errors)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize services
        self.ai_service: Optional[AzureAIAgentService] = None
        self.openai_service: Optional[AzureOpenAIService] = None
        self.sql_service: Optional[AzureSQLService] = None
        self.blob_service: Optional[AzureBlobService] = None
        self.semantic_kernel_service: Optional[SemanticKernelService] = None
        
        # Service initialization status
        self.services_initialized = False
        self.initialization_errors = []
        
        self.logger.info("Infrastructure Service created")
    
    async def initialize_services(self) -> bool:
        """Inicializa todos los servicios Azure"""
        
        self.logger.info("Initializing Azure services...")
        
        try:
            # Initialize Azure AI Agent Service
            await self._initialize_ai_service()
            
            # Initialize Azure OpenAI Service
            await self._initialize_openai_service()
            
            # Initialize Azure SQL Database Service
            await self._initialize_sql_service()
            
            # Initialize Azure Blob Storage Service
            await self._initialize_blob_service()
            
            # Initialize Semantic Kernel Service
            await self._initialize_semantic_kernel_service()
            
            self.services_initialized = True
            self.logger.info("All Azure services initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            self.initialization_errors.append(str(e))
            return False
    
    async def _initialize_ai_service(self):
        """Inicializa Azure AI Agent Service"""
        try:
            self.ai_service = AzureAIAgentService(self.config.ai_service)
            
            # Register infrastructure agents
            self.ai_service.register_infrastructure_agents()
            
            # Create risk evaluation workflow
            workflow_id = self.ai_service.create_risk_evaluation_workflow()
            
            self.logger.info(f"Azure AI Agent Service initialized with workflow: {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Agent Service: {e}")
            raise
    
    async def _initialize_openai_service(self):
        """Inicializa Azure OpenAI Service"""
        try:
            # Configure security proxy
            security_config = SecurityProxyConfig(
                enable_content_filtering=True,
                enable_pii_detection=True,
                enable_audit_logging=True,
                max_tokens_per_request=4000,
                rate_limit_requests_per_minute=60
            )
            
            self.openai_service = AzureOpenAIService(
                self.config.openai,
                security_config
            )
            
            # Test connection
            health_status = self.openai_service.get_service_health()
            if health_status["status"] != "healthy":
                raise Exception(f"OpenAI service unhealthy: {health_status}")
            
            self.logger.info("Azure OpenAI Service initialized with security proxy")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI Service: {e}")
            raise
    
    async def _initialize_sql_service(self):
        """Inicializa Azure SQL Database Service"""
        try:
            self.sql_service = AzureSQLService(self.config.sql_database)
            
            # Test connection and schema
            health_status = self.sql_service.health_check()
            if health_status["status"] != "healthy":
                raise Exception(f"SQL service unhealthy: {health_status}")
            
            self.logger.info("Azure SQL Database Service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SQL Service: {e}")
            raise
    
    async def _initialize_blob_service(self):
        """Inicializa Azure Blob Storage Service"""
        try:
            self.blob_service = AzureBlobService(self.config.blob_storage)
            
            # Test connection
            health_status = self.blob_service.health_check()
            if health_status["status"] != "healthy":
                raise Exception(f"Blob service unhealthy: {health_status}")
            
            self.logger.info("Azure Blob Storage Service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Blob Service: {e}")
            raise
    
    async def _initialize_semantic_kernel_service(self):
        """Inicializa Semantic Kernel Service"""
        try:
            self.semantic_kernel_service = SemanticKernelService(
                self.config.semantic_kernel,
                self.config.openai
            )
            
            # Test functionality
            health_status = self.semantic_kernel_service.health_check()
            if health_status["status"] != "healthy":
                raise Exception(f"Semantic Kernel service unhealthy: {health_status}")
            
            self.logger.info("Semantic Kernel Service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Semantic Kernel Service: {e}")
            raise
    
    # Service Access Methods
    
    def get_ai_service(self) -> AzureAIAgentService:
        """Obtiene el servicio de Azure AI Agent"""
        if not self.ai_service:
            raise RuntimeError("AI Agent Service not initialized")
        return self.ai_service
    
    def get_openai_service(self) -> AzureOpenAIService:
        """Obtiene el servicio de Azure OpenAI"""
        if not self.openai_service:
            raise RuntimeError("OpenAI Service not initialized")
        return self.openai_service
    
    def get_sql_service(self) -> AzureSQLService:
        """Obtiene el servicio de Azure SQL Database"""
        if not self.sql_service:
            raise RuntimeError("SQL Service not initialized")
        return self.sql_service
    
    def get_blob_service(self) -> AzureBlobService:
        """Obtiene el servicio de Azure Blob Storage"""
        if not self.blob_service:
            raise RuntimeError("Blob Service not initialized")
        return self.blob_service
    
    def get_semantic_kernel_service(self) -> SemanticKernelService:
        """Obtiene el servicio de Semantic Kernel"""
        if not self.semantic_kernel_service:
            raise RuntimeError("Semantic Kernel Service not initialized")
        return self.semantic_kernel_service
    
    # High-level Operations
    
    async def start_risk_evaluation(self, company_data: Dict[str, Any]) -> str:
        """Inicia una nueva evaluación de riesgo"""
        
        if not self.services_initialized:
            raise RuntimeError("Services not initialized")
        
        try:
            # Generate evaluation ID
            evaluation_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{company_data.get('company_id', 'unknown')}"
            
            # Create evaluation context in Semantic Kernel
            context = self.semantic_kernel_service.create_evaluation_context(
                evaluation_id, company_data
            )
            
            # Create evaluation record in SQL Database
            from .services.azure_sql_service import RiskEvaluation
            evaluation = RiskEvaluation(
                evaluation_id=evaluation_id,
                company_id=company_data.get("company_id", ""),
                company_name=company_data.get("company_name", ""),
                status="pending",
                created_date=datetime.now(),
                metadata=json.dumps({"source": "infrastructure_service"})
            )
            
            success = self.sql_service.create_risk_evaluation(evaluation)
            if not success:
                raise Exception("Failed to create evaluation record")
            
            # Start workflow execution
            workflow_execution_id = await self.ai_service.execute_workflow(
                "risk_evaluation_workflow",
                company_data
            )
            
            # Update context with workflow execution ID
            self.semantic_kernel_service.update_workflow_state(
                evaluation_id,
                {
                    "workflow_execution_id": workflow_execution_id,
                    "status": "in_progress",
                    "current_phase": "security_validation"
                }
            )
            
            self.logger.info(f"Started risk evaluation: {evaluation_id}")
            return evaluation_id
            
        except Exception as e:
            self.logger.error(f"Failed to start risk evaluation: {e}")
            raise
    
    async def get_evaluation_status(self, evaluation_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una evaluación"""
        
        try:
            # Get from SQL Database
            evaluation = self.sql_service.get_risk_evaluation(evaluation_id)
            if not evaluation:
                return {"error": "Evaluation not found"}
            
            # Get context from Semantic Kernel
            context = self.semantic_kernel_service.get_evaluation_context(evaluation_id)
            
            # Get agent results
            agent_results = self.sql_service.get_agent_results_by_evaluation(evaluation_id)
            
            status = {
                "evaluation_id": evaluation_id,
                "company_id": evaluation.company_id,
                "company_name": evaluation.company_name,
                "status": evaluation.status,
                "final_score": evaluation.final_score,
                "risk_level": evaluation.risk_level,
                "confidence_score": evaluation.confidence_score,
                "created_date": evaluation.created_date.isoformat() if evaluation.created_date else None,
                "completed_date": evaluation.completed_date.isoformat() if evaluation.completed_date else None,
                "workflow_state": context.workflow_state if context else {},
                "agent_results_count": len(agent_results),
                "last_updated": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get evaluation status: {e}")
            return {"error": str(e)}
    
    async def generate_final_report(self, evaluation_id: str) -> Optional[str]:
        """Genera el reporte final de una evaluación"""
        
        try:
            # Get evaluation data
            evaluation = self.sql_service.get_risk_evaluation(evaluation_id)
            if not evaluation:
                raise Exception("Evaluation not found")
            
            # Get scoring details
            scoring_details = self.sql_service.get_scoring_details(evaluation_id)
            
            # Get agent results
            agent_results = self.sql_service.get_agent_results_by_evaluation(evaluation_id)
            
            # Prepare report data
            report_data = {
                "evaluation": evaluation,
                "scoring_details": scoring_details,
                "agent_results": agent_results,
                "generated_date": datetime.now().isoformat()
            }
            
            # Generate report using OpenAI
            report_request = {
                "request_id": f"report_{evaluation_id}",
                "user_id": "system",
                "agent_id": "report_generator",
                "prompt": f"Generate comprehensive risk evaluation report for: {json.dumps(report_data, default=str)}",
                "max_tokens": 3000,
                "temperature": 0.2,
                "timestamp": datetime.now()
            }
            
            # This would be implemented with actual report generation logic
            # For now, save the report data as JSON
            report_blob_path = self.blob_service.save_scoring_report(
                evaluation_id, report_data
            )
            
            self.logger.info(f"Generated final report: {report_blob_path}")
            return report_blob_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate final report: {e}")
            return None
    
    # Health and Monitoring
    
    async def get_infrastructure_status(self) -> InfrastructureStatus:
        """Obtiene el estado completo de la infraestructura"""
        
        services_status = {}
        error_count = 0
        warnings = []
        
        # Check each service
        services = [
            ("ai_service", self.ai_service),
            ("openai_service", self.openai_service),
            ("sql_service", self.sql_service),
            ("blob_service", self.blob_service),
            ("semantic_kernel_service", self.semantic_kernel_service)
        ]
        
        for service_name, service in services:
            if service:
                try:
                    health_status = service.health_check()
                    services_status[service_name] = health_status
                    
                    if health_status.get("status") != "healthy":
                        error_count += 1
                        warnings.append(f"{service_name} is unhealthy")
                        
                except Exception as e:
                    services_status[service_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    error_count += 1
                    warnings.append(f"{service_name} health check failed")
            else:
                services_status[service_name] = {
                    "status": "not_initialized"
                }
                error_count += 1
                warnings.append(f"{service_name} not initialized")
        
        # Determine overall status
        if error_count == 0:
            overall_status = "healthy"
        elif error_count < len(services):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return InfrastructureStatus(
            overall_status=overall_status,
            services_status=services_status,
            last_check=datetime.now(),
            error_count=error_count,
            warnings=warnings
        )
    
    async def get_infrastructure_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de la infraestructura"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "services_initialized": self.services_initialized,
            "initialization_errors": self.initialization_errors
        }
        
        if self.sql_service:
            metrics["database_stats"] = self.sql_service.get_evaluation_statistics()
        
        if self.blob_service:
            metrics["storage_stats"] = self.blob_service.get_storage_statistics()
        
        if self.openai_service:
            metrics["openai_usage"] = self.openai_service.get_usage_statistics()
        
        if self.semantic_kernel_service:
            metrics["memory_stats"] = self.semantic_kernel_service.get_memory_statistics()
        
        return metrics
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Limpia datos antiguos de todos los servicios"""
        
        cleanup_results = {
            "timestamp": datetime.now().isoformat(),
            "days_to_keep": days_to_keep,
            "results": {}
        }
        
        # Cleanup blob storage
        if self.blob_service:
            try:
                blob_cleanup = self.blob_service.cleanup_old_data(days_to_keep)
                cleanup_results["results"]["blob_storage"] = blob_cleanup
            except Exception as e:
                cleanup_results["results"]["blob_storage"] = {"error": str(e)}
        
        # Cleanup semantic kernel contexts
        if self.semantic_kernel_service:
            try:
                memory_cleanup = self.semantic_kernel_service.cleanup_old_contexts(days_to_keep)
                cleanup_results["results"]["semantic_kernel"] = memory_cleanup
            except Exception as e:
                cleanup_results["results"]["semantic_kernel"] = {"error": str(e)}
        
        self.logger.info(f"Cleanup completed: {cleanup_results}")
        return cleanup_results
    
    async def shutdown(self):
        """Cierra todos los servicios de manera ordenada"""
        
        self.logger.info("Shutting down infrastructure services...")
        
        # Close database connections
        if self.sql_service and hasattr(self.sql_service, 'connection_pool'):
            # Close connection pool if needed
            pass
        
        # Clear memory contexts
        if self.semantic_kernel_service:
            self.semantic_kernel_service.evaluation_contexts.clear()
            self.semantic_kernel_service.agent_memories.clear()
        
        self.services_initialized = False
        self.logger.info("Infrastructure services shutdown completed")


# Global infrastructure service instance
_infrastructure_service: Optional[InfrastructureService] = None


def get_infrastructure_service() -> InfrastructureService:
    """Obtiene la instancia global del servicio de infraestructura"""
    global _infrastructure_service
    
    if _infrastructure_service is None:
        _infrastructure_service = InfrastructureService()
    
    return _infrastructure_service


async def initialize_infrastructure() -> bool:
    """Inicializa la infraestructura global"""
    service = get_infrastructure_service()
    return await service.initialize_services()