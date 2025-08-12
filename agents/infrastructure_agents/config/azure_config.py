"""
Azure Services Configuration
Configuración de servicios Azure para agentes de infraestructura
"""

import os
from dataclasses import dataclass
from typing import Optional
from azure.identity import DefaultAzureCredential


@dataclass
class AzureAIServiceConfig:
    """Configuración para Azure AI Agent Service"""
    subscription_id: str
    resource_group: str
    location: str = "eastus"
    endpoint: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'AzureAIServiceConfig':
        return cls(
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", ""),
            resource_group=os.getenv("AZURE_RESOURCE_GROUP", "rg-infrastructure-agents"),
            location=os.getenv("AZURE_LOCATION", "eastus"),
            endpoint=os.getenv("AZURE_AI_SERVICE_ENDPOINT")
        )


@dataclass
class AzureOpenAIConfig:
    """Configuración para Azure OpenAI Service"""
    endpoint: str
    api_key: str
    api_version: str = "2024-02-01"
    deployment_name: str = "gpt-4o"
    model_name: str = "gpt-4o"
    deployment_name_mini: str = "o3-mini"
    model_name_mini: str = "o3-mini"
    max_tokens: int = 4000
    temperature: float = 0.3
    
    @classmethod
    def from_env(cls) -> 'AzureOpenAIConfig':
        return cls(
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            model_name=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
            deployment_name_mini=os.getenv("AZURE_OPENAI_DEPLOYMENT_MINI", "o3-mini"),
            model_name_mini=os.getenv("AZURE_OPENAI_MODEL_MINI", "o3-mini")
        )


@dataclass
class AzureSQLConfig:
    """Configuración para Azure SQL Database"""
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    port: int = 1433
    encrypt: bool = True
    trust_server_certificate: bool = False
    
    @classmethod
    def from_env(cls) -> 'AzureSQLConfig':
        return cls(
            server=os.getenv("AZURE_SQL_SERVER", ""),
            database=os.getenv("AZURE_SQL_DATABASE", "risk_evaluation_db"),
            username=os.getenv("AZURE_SQL_USERNAME", ""),
            password=os.getenv("AZURE_SQL_PASSWORD", ""),
            driver=os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
        )
    
    @property
    def connection_string(self) -> str:
        """Genera connection string para PyODBC"""
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"Encrypt={'yes' if self.encrypt else 'no'};"
            f"TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'};"
        )


@dataclass
class AzureBlobConfig:
    """Configuración para Azure Blob Storage"""
    account_name: str
    account_key: str
    container_reports: str = "risk-reports"
    container_simulations: str = "scenario-simulations"
    container_configs: str = "agent-configurations"
    container_audit: str = "audit-logs"
    
    @classmethod
    def from_env(cls) -> 'AzureBlobConfig':
        return cls(
            account_name=os.getenv("AZURE_STORAGE_ACCOUNT", ""),
            account_key=os.getenv("AZURE_STORAGE_KEY", ""),
            container_reports=os.getenv("AZURE_BLOB_REPORTS", "risk-reports"),
            container_simulations=os.getenv("AZURE_BLOB_SIMULATIONS", "scenario-simulations"),
            container_configs=os.getenv("AZURE_BLOB_CONFIGS", "agent-configurations"),
            container_audit=os.getenv("AZURE_BLOB_AUDIT", "audit-logs")
        )
    
    @property
    def connection_string(self) -> str:
        """Genera connection string para Azure Blob Storage"""
        return f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"


@dataclass
class SemanticKernelConfig:
    """Configuración para Semantic Kernel"""
    memory_store_type: str = "volatile"
    context_window_size: int = 8000
    max_memory_entries: int = 1000
    enable_planning: bool = True
    
    @classmethod
    def from_env(cls) -> 'SemanticKernelConfig':
        return cls(
            memory_store_type=os.getenv("SK_MEMORY_STORE", "volatile"),
            context_window_size=int(os.getenv("SK_CONTEXT_WINDOW", "8000")),
            max_memory_entries=int(os.getenv("SK_MAX_MEMORY", "1000")),
            enable_planning=os.getenv("SK_ENABLE_PLANNING", "true").lower() == "true"
        )


@dataclass
class BingSearchConfig:
    """Configuración para Bing Search Grounding"""
    api_key: str
    endpoint: str = "https://api.bing.microsoft.com/v7.0/search"
    market: str = "es-EC"  # Ecuador market
    safe_search: str = "Moderate"
    
    @classmethod
    def from_env(cls) -> 'BingSearchConfig':
        return cls(
            api_key=os.getenv("BING_SEARCH_API_KEY", ""),
            endpoint=os.getenv("BING_SEARCH_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"),
            market=os.getenv("BING_SEARCH_MARKET", "es-EC"),
            safe_search=os.getenv("BING_SEARCH_SAFE", "Moderate")
        )


class AzureInfrastructureConfig:
    """Configuración principal para toda la infraestructura Azure"""
    
    def __init__(self):
        self.ai_service = AzureAIServiceConfig.from_env()
        self.openai = AzureOpenAIConfig.from_env()
        self.sql_database = AzureSQLConfig.from_env()
        self.blob_storage = AzureBlobConfig.from_env()
        self.semantic_kernel = SemanticKernelConfig.from_env()
        self.bing_search = BingSearchConfig.from_env()
        self.credential = DefaultAzureCredential()
    
    def validate_config(self) -> list[str]:
        """Valida que todas las configuraciones requeridas estén presentes"""
        errors = []
        
        # Critical services (must have for core functionality)
        if not self.openai.endpoint:
            errors.append("AZURE_OPENAI_ENDPOINT is required")
        
        if not self.openai.api_key:
            errors.append("AZURE_OPENAI_API_KEY is required")
        
        # Optional services (warnings only)
        warnings = []
        
        if not self.ai_service.subscription_id:
            warnings.append("AZURE_SUBSCRIPTION_ID recommended for full functionality")
        
        if not self.sql_database.server:
            warnings.append("AZURE_SQL_SERVER recommended for data persistence")
        
        if not self.sql_database.username:
            warnings.append("AZURE_SQL_USERNAME recommended for data persistence")
        
        if not self.sql_database.password:
            warnings.append("AZURE_SQL_PASSWORD recommended for data persistence")
        
        if not self.blob_storage.account_name:
            warnings.append("AZURE_STORAGE_ACCOUNT recommended for file storage")
        
        if not self.blob_storage.account_key:
            warnings.append("AZURE_STORAGE_KEY recommended for file storage")
        
        if not self.bing_search.api_key:
            warnings.append("BING_SEARCH_API_KEY recommended for enhanced search")
        
        # Log warnings but don't block execution
        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(warning)
        
        return errors