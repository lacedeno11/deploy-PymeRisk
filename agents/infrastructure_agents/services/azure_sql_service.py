"""
Azure SQL Database Service
Servicio de base de datos para persistencia de evaluaciones y scoring
"""

import pyodbc
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager
import threading
from queue import Queue

from ..config.azure_config import AzureSQLConfig


@dataclass
class RiskEvaluation:
    """Modelo de datos para evaluaciones de riesgo"""
    evaluation_id: str
    company_id: str
    company_name: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    final_score: Optional[float] = None
    risk_level: Optional[str] = None  # 'alto', 'medio', 'bajo'
    confidence_score: Optional[float] = None
    created_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    metadata: Optional[str] = None  # JSON string


@dataclass
class AgentResult:
    """Modelo de datos para resultados de agentes"""
    result_id: str
    evaluation_id: str
    agent_name: str
    agent_type: str  # 'security', 'business', 'infrastructure'
    result_data: str  # JSON string
    confidence_score: float
    processing_time_ms: int
    created_date: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class ScenarioSimulation:
    """Modelo de datos para simulaciones de escenarios"""
    simulation_id: str
    evaluation_id: str
    scenario_name: str
    variable_changes: str  # JSON string
    original_score: float
    simulated_score: float
    impact_analysis: str  # JSON string
    viability_score: float
    created_date: Optional[datetime] = None


@dataclass
class ScoringDetail:
    """Modelo de datos para detalles de scoring"""
    scoring_id: str
    evaluation_id: str
    financial_score: float
    reputational_score: float
    behavioral_score: float
    final_score: float
    explanation: str
    contributing_factors: str  # JSON string
    credit_recommendation: Optional[str] = None  # JSON string
    created_date: Optional[datetime] = None


class ConnectionPool:
    """Pool de conexiones para Azure SQL Database"""
    
    def __init__(self, connection_string: str, pool_size: int = 10):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializa el pool de conexiones"""
        for _ in range(self.pool_size):
            try:
                conn = pyodbc.connect(self.connection_string)
                self.pool.put(conn)
            except Exception as e:
                self.logger.error(f"Failed to create connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener conexión del pool"""
        conn = None
        try:
            conn = self.pool.get(timeout=30)
            yield conn
        except Exception as e:
            self.logger.error(f"Connection pool error: {e}")
            raise
        finally:
            if conn:
                try:
                    # Test connection before returning to pool
                    conn.execute("SELECT 1")
                    self.pool.put(conn)
                except:
                    # Connection is broken, create new one
                    try:
                        new_conn = pyodbc.connect(self.connection_string)
                        self.pool.put(new_conn)
                    except Exception as e:
                        self.logger.error(f"Failed to recreate connection: {e}")


class AzureSQLService:
    """
    Servicio de Azure SQL Database para agentes de infraestructura
    Maneja persistencia de evaluaciones, scoring y simulaciones
    """
    
    def __init__(self, config: AzureSQLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection_pool = ConnectionPool(config.connection_string)
        
        # Initialize database schema
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Inicializa el esquema de base de datos"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create tables
                self._create_risk_evaluations_table(cursor)
                self._create_agent_results_table(cursor)
                self._create_scenario_simulations_table(cursor)
                self._create_scoring_details_table(cursor)
                self._create_indexes(cursor)
                
                conn.commit()
                self.logger.info("Database schema initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def _create_risk_evaluations_table(self, cursor):
        """Crea la tabla de evaluaciones de riesgo"""
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RiskEvaluations' AND xtype='U')
        CREATE TABLE RiskEvaluations (
            evaluation_id NVARCHAR(50) PRIMARY KEY,
            company_id NVARCHAR(50) NOT NULL,
            company_name NVARCHAR(200) NOT NULL,
            status NVARCHAR(20) NOT NULL DEFAULT 'pending',
            final_score FLOAT NULL,
            risk_level NVARCHAR(10) NULL,
            confidence_score FLOAT NULL,
            created_date DATETIME2 DEFAULT GETDATE(),
            completed_date DATETIME2 NULL,
            metadata NVARCHAR(MAX) NULL,
            INDEX IX_RiskEvaluations_CompanyId (company_id),
            INDEX IX_RiskEvaluations_Status (status),
            INDEX IX_RiskEvaluations_CreatedDate (created_date)
        )
        """
        cursor.execute(sql)
    
    def _create_agent_results_table(self, cursor):
        """Crea la tabla de resultados de agentes"""
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='AgentResults' AND xtype='U')
        CREATE TABLE AgentResults (
            result_id NVARCHAR(50) PRIMARY KEY,
            evaluation_id NVARCHAR(50) NOT NULL,
            agent_name NVARCHAR(50) NOT NULL,
            agent_type NVARCHAR(20) NOT NULL,
            result_data NVARCHAR(MAX) NOT NULL,
            confidence_score FLOAT NOT NULL,
            processing_time_ms INT NOT NULL,
            created_date DATETIME2 DEFAULT GETDATE(),
            error_message NVARCHAR(MAX) NULL,
            FOREIGN KEY (evaluation_id) REFERENCES RiskEvaluations(evaluation_id),
            INDEX IX_AgentResults_EvaluationId (evaluation_id),
            INDEX IX_AgentResults_AgentName (agent_name),
            INDEX IX_AgentResults_AgentType (agent_type)
        )
        """
        cursor.execute(sql)
    
    def _create_scenario_simulations_table(self, cursor):
        """Crea la tabla de simulaciones de escenarios"""
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ScenarioSimulations' AND xtype='U')
        CREATE TABLE ScenarioSimulations (
            simulation_id NVARCHAR(50) PRIMARY KEY,
            evaluation_id NVARCHAR(50) NOT NULL,
            scenario_name NVARCHAR(100) NOT NULL,
            variable_changes NVARCHAR(MAX) NOT NULL,
            original_score FLOAT NOT NULL,
            simulated_score FLOAT NOT NULL,
            impact_analysis NVARCHAR(MAX) NOT NULL,
            viability_score FLOAT NOT NULL,
            created_date DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (evaluation_id) REFERENCES RiskEvaluations(evaluation_id),
            INDEX IX_ScenarioSimulations_EvaluationId (evaluation_id),
            INDEX IX_ScenarioSimulations_CreatedDate (created_date)
        )
        """
        cursor.execute(sql)
    
    def _create_scoring_details_table(self, cursor):
        """Crea la tabla de detalles de scoring"""
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ScoringDetails' AND xtype='U')
        CREATE TABLE ScoringDetails (
            scoring_id NVARCHAR(50) PRIMARY KEY,
            evaluation_id NVARCHAR(50) NOT NULL,
            financial_score FLOAT NOT NULL,
            reputational_score FLOAT NOT NULL,
            behavioral_score FLOAT NOT NULL,
            final_score FLOAT NOT NULL,
            explanation NVARCHAR(MAX) NOT NULL,
            contributing_factors NVARCHAR(MAX) NOT NULL,
            credit_recommendation NVARCHAR(MAX) NULL,
            created_date DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (evaluation_id) REFERENCES RiskEvaluations(evaluation_id),
            INDEX IX_ScoringDetails_EvaluationId (evaluation_id),
            INDEX IX_ScoringDetails_FinalScore (final_score)
        )
        """
        cursor.execute(sql)
    
    def _create_indexes(self, cursor):
        """Crea índices adicionales para optimización"""
        indexes = [
            "CREATE INDEX IX_RiskEvaluations_RiskLevel ON RiskEvaluations(risk_level) WHERE risk_level IS NOT NULL",
            "CREATE INDEX IX_AgentResults_ProcessingTime ON AgentResults(processing_time_ms)",
            "CREATE INDEX IX_ScenarioSimulations_SimulatedScore ON ScenarioSimulations(simulated_score)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except pyodbc.Error as e:
                # Index might already exist
                if "already exists" not in str(e):
                    self.logger.warning(f"Failed to create index: {e}")
    
    # Risk Evaluations CRUD Operations
    
    def create_risk_evaluation(self, evaluation: RiskEvaluation) -> bool:
        """Crea una nueva evaluación de riesgo"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                INSERT INTO RiskEvaluations 
                (evaluation_id, company_id, company_name, status, final_score, 
                 risk_level, confidence_score, created_date, completed_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    evaluation.evaluation_id,
                    evaluation.company_id,
                    evaluation.company_name,
                    evaluation.status,
                    evaluation.final_score,
                    evaluation.risk_level,
                    evaluation.confidence_score,
                    evaluation.created_date or datetime.now(),
                    evaluation.completed_date,
                    evaluation.metadata
                ))
                
                conn.commit()
                self.logger.info(f"Risk evaluation created: {evaluation.evaluation_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create risk evaluation: {e}")
            return False
    
    def get_risk_evaluation(self, evaluation_id: str) -> Optional[RiskEvaluation]:
        """Obtiene una evaluación de riesgo por ID"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT evaluation_id, company_id, company_name, status, final_score,
                       risk_level, confidence_score, created_date, completed_date, metadata
                FROM RiskEvaluations 
                WHERE evaluation_id = ?
                """
                
                cursor.execute(sql, (evaluation_id,))
                row = cursor.fetchone()
                
                if row:
                    return RiskEvaluation(
                        evaluation_id=row[0],
                        company_id=row[1],
                        company_name=row[2],
                        status=row[3],
                        final_score=row[4],
                        risk_level=row[5],
                        confidence_score=row[6],
                        created_date=row[7],
                        completed_date=row[8],
                        metadata=row[9]
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get risk evaluation: {e}")
            return None
    
    def update_risk_evaluation_status(self, evaluation_id: str, status: str, 
                                    final_score: float = None, 
                                    risk_level: str = None,
                                    confidence_score: float = None) -> bool:
        """Actualiza el estado de una evaluación de riesgo"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                UPDATE RiskEvaluations 
                SET status = ?, final_score = ?, risk_level = ?, confidence_score = ?,
                    completed_date = CASE WHEN ? = 'completed' THEN GETDATE() ELSE completed_date END
                WHERE evaluation_id = ?
                """
                
                cursor.execute(sql, (status, final_score, risk_level, confidence_score, status, evaluation_id))
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to update risk evaluation status: {e}")
            return False
    
    # Agent Results CRUD Operations
    
    def save_agent_result(self, result: AgentResult) -> bool:
        """Guarda el resultado de un agente"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                INSERT INTO AgentResults 
                (result_id, evaluation_id, agent_name, agent_type, result_data,
                 confidence_score, processing_time_ms, created_date, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    result.result_id,
                    result.evaluation_id,
                    result.agent_name,
                    result.agent_type,
                    result.result_data,
                    result.confidence_score,
                    result.processing_time_ms,
                    result.created_date or datetime.now(),
                    result.error_message
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save agent result: {e}")
            return False
    
    def get_agent_results_by_evaluation(self, evaluation_id: str) -> List[AgentResult]:
        """Obtiene todos los resultados de agentes para una evaluación"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT result_id, evaluation_id, agent_name, agent_type, result_data,
                       confidence_score, processing_time_ms, created_date, error_message
                FROM AgentResults 
                WHERE evaluation_id = ?
                ORDER BY created_date
                """
                
                cursor.execute(sql, (evaluation_id,))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append(AgentResult(
                        result_id=row[0],
                        evaluation_id=row[1],
                        agent_name=row[2],
                        agent_type=row[3],
                        result_data=row[4],
                        confidence_score=row[5],
                        processing_time_ms=row[6],
                        created_date=row[7],
                        error_message=row[8]
                    ))
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to get agent results: {e}")
            return []
    
    # Scoring Details CRUD Operations
    
    def save_scoring_details(self, scoring: ScoringDetail) -> bool:
        """Guarda los detalles de scoring"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                INSERT INTO ScoringDetails 
                (scoring_id, evaluation_id, financial_score, reputational_score,
                 behavioral_score, final_score, explanation, contributing_factors,
                 credit_recommendation, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    scoring.scoring_id,
                    scoring.evaluation_id,
                    scoring.financial_score,
                    scoring.reputational_score,
                    scoring.behavioral_score,
                    scoring.final_score,
                    scoring.explanation,
                    scoring.contributing_factors,
                    scoring.credit_recommendation,
                    scoring.created_date or datetime.now()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save scoring details: {e}")
            return False
    
    def get_scoring_details(self, evaluation_id: str) -> Optional[ScoringDetail]:
        """Obtiene los detalles de scoring para una evaluación"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT scoring_id, evaluation_id, financial_score, reputational_score,
                       behavioral_score, final_score, explanation, contributing_factors,
                       credit_recommendation, created_date
                FROM ScoringDetails 
                WHERE evaluation_id = ?
                """
                
                cursor.execute(sql, (evaluation_id,))
                row = cursor.fetchone()
                
                if row:
                    return ScoringDetail(
                        scoring_id=row[0],
                        evaluation_id=row[1],
                        financial_score=row[2],
                        reputational_score=row[3],
                        behavioral_score=row[4],
                        final_score=row[5],
                        explanation=row[6],
                        contributing_factors=row[7],
                        credit_recommendation=row[8],
                        created_date=row[9]
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get scoring details: {e}")
            return None
    
    # Scenario Simulations CRUD Operations
    
    def save_scenario_simulation(self, simulation: ScenarioSimulation) -> bool:
        """Guarda una simulación de escenario"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                INSERT INTO ScenarioSimulations 
                (simulation_id, evaluation_id, scenario_name, variable_changes,
                 original_score, simulated_score, impact_analysis, viability_score, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    simulation.simulation_id,
                    simulation.evaluation_id,
                    simulation.scenario_name,
                    simulation.variable_changes,
                    simulation.original_score,
                    simulation.simulated_score,
                    simulation.impact_analysis,
                    simulation.viability_score,
                    simulation.created_date or datetime.now()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save scenario simulation: {e}")
            return False
    
    def get_scenario_simulations(self, evaluation_id: str) -> List[ScenarioSimulation]:
        """Obtiene todas las simulaciones para una evaluación"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT simulation_id, evaluation_id, scenario_name, variable_changes,
                       original_score, simulated_score, impact_analysis, viability_score, created_date
                FROM ScenarioSimulations 
                WHERE evaluation_id = ?
                ORDER BY created_date DESC
                """
                
                cursor.execute(sql, (evaluation_id,))
                rows = cursor.fetchall()
                
                simulations = []
                for row in rows:
                    simulations.append(ScenarioSimulation(
                        simulation_id=row[0],
                        evaluation_id=row[1],
                        scenario_name=row[2],
                        variable_changes=row[3],
                        original_score=row[4],
                        simulated_score=row[5],
                        impact_analysis=row[6],
                        viability_score=row[7],
                        created_date=row[8]
                    ))
                
                return simulations
                
        except Exception as e:
            self.logger.error(f"Failed to get scenario simulations: {e}")
            return []
    
    # Analytics and Reporting
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de evaluaciones"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total evaluations
                cursor.execute("SELECT COUNT(*) FROM RiskEvaluations")
                total_evaluations = cursor.fetchone()[0]
                
                # Evaluations by status
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM RiskEvaluations 
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())
                
                # Evaluations by risk level
                cursor.execute("""
                    SELECT risk_level, COUNT(*) 
                    FROM RiskEvaluations 
                    WHERE risk_level IS NOT NULL
                    GROUP BY risk_level
                """)
                risk_level_counts = dict(cursor.fetchall())
                
                # Average processing time
                cursor.execute("""
                    SELECT AVG(DATEDIFF(minute, created_date, completed_date))
                    FROM RiskEvaluations 
                    WHERE completed_date IS NOT NULL
                """)
                avg_processing_time = cursor.fetchone()[0] or 0
                
                return {
                    "total_evaluations": total_evaluations,
                    "status_distribution": status_counts,
                    "risk_level_distribution": risk_level_counts,
                    "average_processing_time_minutes": avg_processing_time,
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get evaluation statistics: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud de la base de datos"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                return {
                    "status": "healthy",
                    "server": self.config.server,
                    "database": self.config.database,
                    "connection_pool_size": self.connection_pool.pool_size,
                    "last_check": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "server": self.config.server,
                "database": self.config.database,
                "last_check": datetime.now().isoformat()
            }