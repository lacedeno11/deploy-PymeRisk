# security/audit_logger.py

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    """
    Define la estructura de un evento de auditoría
    """
    timestamp: str = Field(description="Timestamp del evento en formato ISO")
    evaluation_id: str = Field(description="ID único de la evaluación")
    event_type: str = Field(description="Tipo de evento: SECURITY_CHECK, INPUT_VALIDATION, BUSINESS_ANALYSIS, OUTPUT_SANITIZATION, SCORING, COMPLETION, ERROR")
    agent_id: str = Field(description="ID del agente que generó el evento")
    user_id: str = Field(description="ID del usuario que inició la evaluación", default="system")
    company_id: str = Field(description="ID de la empresa evaluada")
    details: Dict[str, Any] = Field(description="Detalles específicos del evento")
    success: bool = Field(description="Indica si la operación fue exitosa")
    processing_time: Optional[float] = Field(description="Tiempo de procesamiento en segundos", default=None)
    tokens_used: Optional[int] = Field(description="Tokens utilizados en la operación", default=None)
    risk_level: Optional[str] = Field(description="Nivel de riesgo detectado", default=None)

class AuditLogger:
    """
    Agente de auditoría que registra todos los eventos del sistema
    """
    
    def __init__(self, log_file_path: str = "audit.log"):
        self.log_file_path = log_file_path
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self):
        """Asegura que el archivo de log existe"""
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                # Write initial log entry
                initial_entry = AuditEvent(
                    timestamp=datetime.now().isoformat(),
                    evaluation_id="system_init",
                    event_type="SYSTEM_INIT",
                    agent_id="audit_logger",
                    company_id="system",
                    details={"message": "Audit log initialized"},
                    success=True
                )
                f.write(initial_entry.model_dump_json() + "\n")
    
    def log_security_supervision(self, evaluation_id: str, company_id: str, 
                               supervision_result: Dict[str, Any], processing_time: float) -> None:
        """Registra evento de supervisión de seguridad"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="SECURITY_SUPERVISION",
            agent_id="security_supervisor",
            company_id=company_id,
            details={
                "anomaly_detected": supervision_result.get("anomaly_detected", False),
                "confidence_score": supervision_result.get("confidence_score", 0.0),
                "recommended_action": supervision_result.get("recommended_action", "Ninguna"),
                "critical_alert": supervision_result.get("critical_alert", False),
                "summary": supervision_result.get("summary", "")
            },
            success=supervision_result.get("success", True),
            processing_time=processing_time,
            risk_level="CRITICAL" if supervision_result.get("critical_alert", False) else "LOW"
        )
        self._write_event(event)
    
    def log_input_validation(self, evaluation_id: str, company_id: str, 
                           validation_result: Dict[str, Any], processing_time: float) -> None:
        """Registra evento de validación de entrada"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="INPUT_VALIDATION",
            agent_id="input_validator",
            company_id=company_id,
            details={
                "all_safe": validation_result.get("all_safe", False),
                "blocked_fields": validation_result.get("blocked_fields", []),
                "overall_risk_level": validation_result.get("overall_risk_level", "UNKNOWN"),
                "field_count": len(validation_result.get("field_results", []))
            },
            success=validation_result.get("success", True),
            processing_time=processing_time,
            risk_level=validation_result.get("overall_risk_level", "UNKNOWN")
        )
        self._write_event(event)
    
    def log_business_analysis(self, evaluation_id: str, company_id: str, agent_type: str,
                            analysis_result: Dict[str, Any], processing_time: float) -> None:
        """Registra evento de análisis de negocio"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="BUSINESS_ANALYSIS",
            agent_id=f"{agent_type}_agent",
            company_id=company_id,
            details={
                "agent_type": agent_type,
                "analysis_successful": analysis_result.get("success", True),
                "tokens_used": analysis_result.get("tokens_used", 0),
                "has_error": "error" in analysis_result
            },
            success=analysis_result.get("success", True),
            processing_time=processing_time,
            tokens_used=analysis_result.get("tokens_used", 0)
        )
        self._write_event(event)
    
    def log_output_sanitization(self, evaluation_id: str, company_id: str, agent_type: str,
                              sanitization_result: Dict[str, Any], processing_time: float) -> None:
        """Registra evento de sanitización de salida"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="OUTPUT_SANITIZATION",
            agent_id="output_sanitizer",
            company_id=company_id,
            details={
                "agent_type": agent_type,
                "sanitization_applied": sanitization_result.get("sanitization_applied", False),
                "pii_detected": sanitization_result.get("pii_detected", False),
                "sensitive_data_types": sanitization_result.get("sensitive_data_types", []),
                "sanitization_details": sanitization_result.get("sanitization_details", "")
            },
            success=sanitization_result.get("success", True),
            processing_time=processing_time
        )
        self._write_event(event)
    
    def log_scoring_consolidation(self, evaluation_id: str, company_id: str,
                                consolidated_result: Dict[str, Any], processing_time: float) -> None:
        """Registra evento de consolidación de scoring"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="SCORING_CONSOLIDATION",
            agent_id="scoring_agent",
            company_id=company_id,
            details={
                "final_score": consolidated_result.get("final_score", 0),
                "risk_level": consolidated_result.get("risk_level", "UNKNOWN"),
                "confidence": consolidated_result.get("confidence", 0.0),
                "contributing_factors_count": len(consolidated_result.get("contributing_factors", [])),
                "has_credit_recommendation": "credit_recommendation" in consolidated_result
            },
            success=consolidated_result.get("success", True),
            processing_time=processing_time,
            tokens_used=consolidated_result.get("tokens_used", 0),
            risk_level=consolidated_result.get("risk_level", "UNKNOWN")
        )
        self._write_event(event)
    
    def log_evaluation_completion(self, evaluation_id: str, company_id: str,
                                final_result: Dict[str, Any], total_processing_time: float,
                                total_tokens_used: int) -> None:
        """Registra la finalización completa de una evaluación"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="EVALUATION_COMPLETED",
            agent_id="master_orchestrator",
            company_id=company_id,
            details={
                "final_score": final_result.get("final_score", 0),
                "risk_level": final_result.get("risk_level", "UNKNOWN"),
                "total_processing_time": total_processing_time,
                "total_tokens_used": total_tokens_used,
                "final_sanitization_applied": final_result.get("final_sanitization_applied", False),
                "evaluation_successful": final_result.get("success", True)
            },
            success=final_result.get("success", True),
            processing_time=total_processing_time,
            tokens_used=total_tokens_used,
            risk_level=final_result.get("risk_level", "UNKNOWN")
        )
        self._write_event(event)
    
    def log_evaluation_failure(self, evaluation_id: str, company_id: str, error_message: str,
                             failure_stage: str, processing_time: float) -> None:
        """Registra el fallo de una evaluación"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="EVALUATION_FAILED",
            agent_id="master_orchestrator",
            company_id=company_id,
            details={
                "error_message": error_message,
                "failure_stage": failure_stage,
                "processing_time": processing_time
            },
            success=False,
            processing_time=processing_time,
            risk_level="ERROR"
        )
        self._write_event(event)
    
    def log_security_alert(self, evaluation_id: str, company_id: str, alert_type: str,
                          alert_details: Dict[str, Any]) -> None:
        """Registra una alerta de seguridad crítica"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            evaluation_id=evaluation_id,
            event_type="SECURITY_ALERT",
            agent_id="security_system",
            company_id=company_id,
            details={
                "alert_type": alert_type,
                "alert_details": alert_details,
                "requires_immediate_attention": True
            },
            success=False,
            risk_level="CRITICAL"
        )
        self._write_event(event)
    
    def _write_event(self, event: AuditEvent) -> None:
        """Escribe un evento al archivo de log"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as e:
            # If we can't write to the audit log, we have a serious problem
            # Try to write to a backup location
            try:
                backup_path = f"{self.log_file_path}.backup"
                with open(backup_path, 'a', encoding='utf-8') as f:
                    error_event = AuditEvent(
                        timestamp=datetime.now().isoformat(),
                        evaluation_id="audit_error",
                        event_type="AUDIT_ERROR",
                        agent_id="audit_logger",
                        company_id="system",
                        details={
                            "original_error": str(e),
                            "failed_event": event.dict(),
                            "backup_location": backup_path
                        },
                        success=False
                    )
                    f.write(error_event.model_dump_json() + "\n")
            except:
                # If even the backup fails, there's nothing more we can do
                pass
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene los eventos más recientes del log"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                
                events = []
                for line in recent_lines:
                    try:
                        event_data = json.loads(line.strip())
                        events.append(event_data)
                    except json.JSONDecodeError:
                        continue
                
                return events
        except FileNotFoundError:
            return []
        except Exception:
            return []
    
    def get_evaluation_audit_trail(self, evaluation_id: str) -> List[Dict[str, Any]]:
        """Obtiene el trail completo de auditoría para una evaluación específica"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                evaluation_events = []
                for line in lines:
                    try:
                        event_data = json.loads(line.strip())
                        if event_data.get("evaluation_id") == evaluation_id:
                            evaluation_events.append(event_data)
                    except json.JSONDecodeError:
                        continue
                
                return evaluation_events
        except FileNotFoundError:
            return []
        except Exception:
            return []

# Factory function
def create_audit_logger(log_file_path: str = "audit.log") -> AuditLogger:
    """Crea una instancia del logger de auditoría"""
    return AuditLogger(log_file_path)