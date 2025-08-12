"""
Azure Blob Storage Service
Servicio de almacenamiento para reportes, simulaciones y configuraciones
"""

import logging
import json
import io
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError, ResourceNotFoundError

from ..config.azure_config import AzureBlobConfig


@dataclass
class BlobMetadata:
    """Metadatos de un blob"""
    name: str
    container: str
    size: int
    last_modified: datetime
    content_type: str
    metadata: Dict[str, str]
    etag: str


@dataclass
class ReportDocument:
    """Documento de reporte"""
    report_id: str
    evaluation_id: str
    report_type: str  # 'final_report', 'scoring_details', 'simulation_summary'
    content: bytes
    content_type: str
    metadata: Dict[str, Any]
    created_date: datetime


class AzureBlobService:
    """
    Servicio de Azure Blob Storage para agentes de infraestructura
    Maneja almacenamiento de reportes, simulaciones y configuraciones
    """
    
    def __init__(self, config: AzureBlobConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Blob Service Client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            config.connection_string
        )
        
        # Initialize containers
        self._initialize_containers()
    
    def _initialize_containers(self):
        """Inicializa los contenedores necesarios"""
        containers = [
            self.config.container_reports,
            self.config.container_simulations,
            self.config.container_configs,
            self.config.container_audit
        ]
        
        for container_name in containers:
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                
                # Create container if it doesn't exist
                if not container_client.exists():
                    container_client.create_container()
                    self.logger.info(f"Created container: {container_name}")
                
                # Set container metadata
                container_client.set_container_metadata({
                    "purpose": self._get_container_purpose(container_name),
                    "created_by": "infrastructure_agents",
                    "created_date": datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Failed to initialize container {container_name}: {e}")
                raise
    
    def _get_container_purpose(self, container_name: str) -> str:
        """Obtiene el propósito de un contenedor"""
        purposes = {
            self.config.container_reports: "Risk evaluation reports and documents",
            self.config.container_simulations: "Scenario simulation results and data",
            self.config.container_configs: "Agent configurations and settings",
            self.config.container_audit: "Audit logs and compliance data"
        }
        return purposes.get(container_name, "General storage")
    
    # Report Management
    
    def save_final_report(self, evaluation_id: str, report_content: bytes, 
                         content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document") -> str:
        """Guarda el reporte final de evaluación"""
        
        blob_name = f"{evaluation_id}/final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        metadata = {
            "evaluation_id": evaluation_id,
            "report_type": "final_report",
            "created_date": datetime.now().isoformat(),
            "content_type": content_type
        }
        
        return self._upload_blob(
            container_name=self.config.container_reports,
            blob_name=blob_name,
            data=report_content,
            content_type=content_type,
            metadata=metadata
        )
    
    def save_scoring_report(self, evaluation_id: str, scoring_data: Dict[str, Any]) -> str:
        """Guarda el reporte detallado de scoring"""
        
        blob_name = f"{evaluation_id}/scoring_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert scoring data to JSON
        json_content = json.dumps(scoring_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "evaluation_id": evaluation_id,
            "report_type": "scoring_details",
            "created_date": datetime.now().isoformat(),
            "final_score": str(scoring_data.get('final_score', 0)),
            "risk_level": scoring_data.get('risk_level', 'unknown')
        }
        
        return self._upload_blob(
            container_name=self.config.container_reports,
            blob_name=blob_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def get_report(self, evaluation_id: str, report_type: str) -> Optional[bytes]:
        """Obtiene un reporte específico"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_reports
            )
            
            # List blobs with the evaluation_id prefix
            blobs = container_client.list_blobs(name_starts_with=f"{evaluation_id}/")
            
            # Find the specific report type
            for blob in blobs:
                if report_type in blob.metadata.get('report_type', ''):
                    blob_client = container_client.get_blob_client(blob.name)
                    return blob_client.download_blob().readall()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get report: {e}")
            return None
    
    def list_reports(self, evaluation_id: str) -> List[BlobMetadata]:
        """Lista todos los reportes para una evaluación"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_reports
            )
            
            blobs = container_client.list_blobs(
                name_starts_with=f"{evaluation_id}/",
                include=['metadata']
            )
            
            reports = []
            for blob in blobs:
                reports.append(BlobMetadata(
                    name=blob.name,
                    container=self.config.container_reports,
                    size=blob.size,
                    last_modified=blob.last_modified,
                    content_type=blob.content_settings.content_type if blob.content_settings else 'unknown',
                    metadata=blob.metadata or {},
                    etag=blob.etag
                ))
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Failed to list reports: {e}")
            return []
    
    # Simulation Management
    
    def save_scenario_simulation(self, evaluation_id: str, simulation_id: str, 
                               simulation_data: Dict[str, Any]) -> str:
        """Guarda los resultados de una simulación de escenario"""
        
        blob_name = f"{evaluation_id}/scenarios/{simulation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert simulation data to JSON
        json_content = json.dumps(simulation_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "evaluation_id": evaluation_id,
            "simulation_id": simulation_id,
            "scenario_name": simulation_data.get('scenario_name', 'unknown'),
            "created_date": datetime.now().isoformat(),
            "original_score": str(simulation_data.get('original_score', 0)),
            "simulated_score": str(simulation_data.get('simulated_score', 0))
        }
        
        return self._upload_blob(
            container_name=self.config.container_simulations,
            blob_name=blob_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def save_simulation_comparison(self, evaluation_id: str, comparison_data: Dict[str, Any]) -> str:
        """Guarda los resultados de comparación de escenarios"""
        
        blob_name = f"{evaluation_id}/comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert comparison data to JSON
        json_content = json.dumps(comparison_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "evaluation_id": evaluation_id,
            "comparison_type": "scenario_comparison",
            "created_date": datetime.now().isoformat(),
            "scenarios_count": str(len(comparison_data.get('scenarios', []))),
            "best_scenario": comparison_data.get('best_scenario', 'unknown')
        }
        
        return self._upload_blob(
            container_name=self.config.container_simulations,
            blob_name=blob_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def get_scenario_simulation(self, evaluation_id: str, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de una simulación específica"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_simulations
            )
            
            # List blobs with the evaluation_id and simulation_id
            blobs = container_client.list_blobs(
                name_starts_with=f"{evaluation_id}/scenarios/{simulation_id}",
                include=['metadata']
            )
            
            for blob in blobs:
                if simulation_id in blob.name:
                    blob_client = container_client.get_blob_client(blob.name)
                    content = blob_client.download_blob().readall()
                    return json.loads(content.decode('utf-8'))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get scenario simulation: {e}")
            return None
    
    def list_scenario_simulations(self, evaluation_id: str) -> List[BlobMetadata]:
        """Lista todas las simulaciones para una evaluación"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_simulations
            )
            
            blobs = container_client.list_blobs(
                name_starts_with=f"{evaluation_id}/",
                include=['metadata']
            )
            
            simulations = []
            for blob in blobs:
                simulations.append(BlobMetadata(
                    name=blob.name,
                    container=self.config.container_simulations,
                    size=blob.size,
                    last_modified=blob.last_modified,
                    content_type=blob.content_settings.content_type if blob.content_settings else 'application/json',
                    metadata=blob.metadata or {},
                    etag=blob.etag
                ))
            
            return simulations
            
        except Exception as e:
            self.logger.error(f"Failed to list scenario simulations: {e}")
            return []
    
    # Configuration Management
    
    def save_agent_configuration(self, agent_id: str, config_data: Dict[str, Any]) -> str:
        """Guarda la configuración de un agente"""
        
        blob_name = f"agents/{agent_id}/config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert config data to JSON
        json_content = json.dumps(config_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "agent_id": agent_id,
            "config_type": "agent_configuration",
            "created_date": datetime.now().isoformat(),
            "version": config_data.get('version', '1.0.0')
        }
        
        return self._upload_blob(
            container_name=self.config.container_configs,
            blob_name=blob_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def get_agent_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración más reciente de un agente"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_configs
            )
            
            # List blobs for the agent, sorted by last modified
            blobs = list(container_client.list_blobs(
                name_starts_with=f"agents/{agent_id}/",
                include=['metadata']
            ))
            
            if not blobs:
                return None
            
            # Get the most recent configuration
            latest_blob = max(blobs, key=lambda b: b.last_modified)
            blob_client = container_client.get_blob_client(latest_blob.name)
            content = blob_client.download_blob().readall()
            
            return json.loads(content.decode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"Failed to get agent configuration: {e}")
            return None
    
    # Audit Logging
    
    def save_audit_log(self, log_type: str, log_data: Dict[str, Any]) -> str:
        """Guarda un log de auditoría"""
        
        date_str = datetime.now().strftime('%Y/%m/%d')
        blob_name = f"{log_type}/{date_str}/audit_{datetime.now().strftime('%H%M%S_%f')}.json"
        
        # Add timestamp to log data
        log_data['timestamp'] = datetime.now().isoformat()
        log_data['log_type'] = log_type
        
        # Convert log data to JSON
        json_content = json.dumps(log_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "log_type": log_type,
            "created_date": datetime.now().isoformat(),
            "severity": log_data.get('severity', 'info')
        }
        
        return self._upload_blob(
            container_name=self.config.container_audit,
            blob_name=blob_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def get_audit_logs(self, log_type: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Obtiene logs de auditoría por tipo y rango de fechas"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.container_audit
            )
            
            logs = []
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y/%m/%d')
                prefix = f"{log_type}/{date_str}/"
                
                blobs = container_client.list_blobs(name_starts_with=prefix)
                
                for blob in blobs:
                    try:
                        blob_client = container_client.get_blob_client(blob.name)
                        content = blob_client.download_blob().readall()
                        log_data = json.loads(content.decode('utf-8'))
                        logs.append(log_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to read audit log {blob.name}: {e}")
                
                current_date += timedelta(days=1)
            
            return sorted(logs, key=lambda x: x.get('timestamp', ''))
            
        except Exception as e:
            self.logger.error(f"Failed to get audit logs: {e}")
            return []
    
    # Backup and Maintenance
    
    def create_backup(self, evaluation_id: str) -> str:
        """Crea un backup completo de todos los datos de una evaluación"""
        
        backup_name = f"backups/{evaluation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Collect all data for the evaluation
        backup_data = {
            "evaluation_id": evaluation_id,
            "backup_date": datetime.now().isoformat(),
            "reports": [],
            "simulations": [],
            "metadata": {}
        }
        
        # Get all reports
        reports = self.list_reports(evaluation_id)
        for report in reports:
            report_content = self.get_report(evaluation_id, report.metadata.get('report_type', ''))
            if report_content:
                backup_data["reports"].append({
                    "name": report.name,
                    "metadata": report.metadata,
                    "content_base64": report_content.hex()  # Store as hex for JSON compatibility
                })
        
        # Get all simulations
        simulations = self.list_scenario_simulations(evaluation_id)
        for simulation in simulations:
            if 'scenarios/' in simulation.name:
                simulation_id = simulation.metadata.get('simulation_id', '')
                simulation_data = self.get_scenario_simulation(evaluation_id, simulation_id)
                if simulation_data:
                    backup_data["simulations"].append(simulation_data)
        
        # Convert backup data to JSON
        json_content = json.dumps(backup_data, indent=2, ensure_ascii=False, default=str)
        content_bytes = json_content.encode('utf-8')
        
        metadata = {
            "evaluation_id": evaluation_id,
            "backup_type": "full_evaluation_backup",
            "created_date": datetime.now().isoformat(),
            "reports_count": str(len(backup_data["reports"])),
            "simulations_count": str(len(backup_data["simulations"]))
        }
        
        return self._upload_blob(
            container_name=self.config.container_configs,
            blob_name=backup_name,
            data=content_bytes,
            content_type="application/json",
            metadata=metadata
        )
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Limpia datos antiguos según política de retención"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleanup_stats = {"deleted_blobs": 0, "errors": 0}
        
        containers_to_clean = [
            self.config.container_reports,
            self.config.container_simulations,
            self.config.container_audit
        ]
        
        for container_name in containers_to_clean:
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                blobs = container_client.list_blobs(include=['metadata'])
                
                for blob in blobs:
                    if blob.last_modified < cutoff_date:
                        try:
                            blob_client = container_client.get_blob_client(blob.name)
                            blob_client.delete_blob()
                            cleanup_stats["deleted_blobs"] += 1
                            self.logger.info(f"Deleted old blob: {blob.name}")
                        except Exception as e:
                            cleanup_stats["errors"] += 1
                            self.logger.error(f"Failed to delete blob {blob.name}: {e}")
                            
            except Exception as e:
                cleanup_stats["errors"] += 1
                self.logger.error(f"Failed to cleanup container {container_name}: {e}")
        
        return cleanup_stats
    
    # Helper Methods
    
    def _upload_blob(self, container_name: str, blob_name: str, data: bytes, 
                    content_type: str, metadata: Dict[str, str]) -> str:
        """Método auxiliar para subir blobs"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                data=data,
                content_settings={
                    "content_type": content_type
                },
                metadata=metadata,
                overwrite=True
            )
            
            self.logger.info(f"Uploaded blob: {container_name}/{blob_name}")
            return f"{container_name}/{blob_name}"
            
        except Exception as e:
            self.logger.error(f"Failed to upload blob: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del servicio de blob storage"""
        try:
            # Test connection by listing containers
            containers = list(self.blob_service_client.list_containers())
            
            container_status = {}
            for container in containers:
                if container.name in [
                    self.config.container_reports,
                    self.config.container_simulations,
                    self.config.container_configs,
                    self.config.container_audit
                ]:
                    container_client = self.blob_service_client.get_container_client(container.name)
                    blob_count = len(list(container_client.list_blobs()))
                    container_status[container.name] = {
                        "exists": True,
                        "blob_count": blob_count,
                        "last_modified": container.last_modified.isoformat() if container.last_modified else None
                    }
            
            return {
                "status": "healthy",
                "account_name": self.config.account_name,
                "containers": container_status,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "account_name": self.config.account_name,
                "last_check": datetime.now().isoformat()
            }
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso de almacenamiento"""
        try:
            stats = {
                "containers": {},
                "total_blobs": 0,
                "total_size_bytes": 0
            }
            
            containers = [
                self.config.container_reports,
                self.config.container_simulations,
                self.config.container_configs,
                self.config.container_audit
            ]
            
            for container_name in containers:
                try:
                    container_client = self.blob_service_client.get_container_client(container_name)
                    blobs = list(container_client.list_blobs())
                    
                    container_stats = {
                        "blob_count": len(blobs),
                        "total_size": sum(blob.size for blob in blobs),
                        "last_modified": max((blob.last_modified for blob in blobs), default=None)
                    }
                    
                    stats["containers"][container_name] = container_stats
                    stats["total_blobs"] += container_stats["blob_count"]
                    stats["total_size_bytes"] += container_stats["total_size"]
                    
                except Exception as e:
                    self.logger.error(f"Failed to get stats for container {container_name}: {e}")
                    stats["containers"][container_name] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {"error": str(e)}