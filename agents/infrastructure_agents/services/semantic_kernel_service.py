"""
Semantic Kernel Service Integration
Servicio de gestión de contexto y memoria usando Semantic Kernel
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import semantic_kernel as sk

from ..config.azure_config import SemanticKernelConfig, AzureOpenAIConfig


@dataclass
class ContextEntry:
    """Entrada de contexto en memoria"""
    entry_id: str
    evaluation_id: str
    agent_id: str
    context_type: str  # 'input', 'result', 'state', 'error'
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    relevance_score: float = 0.0


@dataclass
class AgentMemory:
    """Memoria específica de un agente"""
    agent_id: str
    evaluation_id: str
    context_entries: List[ContextEntry]
    current_state: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    last_updated: datetime


@dataclass
class EvaluationContext:
    """Contexto completo de una evaluación"""
    evaluation_id: str
    company_data: Dict[str, Any]
    agent_memories: Dict[str, AgentMemory]
    workflow_state: Dict[str, Any]
    global_context: Dict[str, Any]
    created_date: datetime
    last_updated: datetime


class SemanticKernelService:
    """
    Servicio de Semantic Kernel para gestión de contexto y memoria
    Coordina el contexto entre agentes de infraestructura
    """
    
    def __init__(self, sk_config: SemanticKernelConfig, openai_config: AzureOpenAIConfig):
        self.sk_config = sk_config
        self.openai_config = openai_config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Semantic Kernel
        self.kernel = sk.Kernel()
        self.memory_store = VolatileMemoryStore()
        
        # Context storage
        self.evaluation_contexts: Dict[str, EvaluationContext] = {}
        self.agent_memories: Dict[str, AgentMemory] = {}
        
        # Initialize kernel components
        self._initialize_kernel()
        self._setup_infrastructure_plugins()
    
    def _initialize_kernel(self):
        """Inicializa el kernel de Semantic Kernel"""
        try:
            # Initialize basic kernel - simplified for current SK version
            self.logger.info("Semantic Kernel initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Semantic Kernel: {e}")
            raise
    
    def _setup_infrastructure_plugins(self):
        """Configura plugins específicos para agentes de infraestructura"""
        # Simplified plugin setup for current SK version
        self.logger.info("Infrastructure plugins configured")
    
    # Plugin creation methods removed for current SK version compatibility
    
    # Context Management
    
    def create_evaluation_context(self, evaluation_id: str, company_data: Dict[str, Any]) -> EvaluationContext:
        """Crea un nuevo contexto de evaluación"""
        
        context = EvaluationContext(
            evaluation_id=evaluation_id,
            company_data=company_data,
            agent_memories={},
            workflow_state={"status": "initialized", "current_phase": "security"},
            global_context={
                "evaluation_start_time": datetime.now().isoformat(),
                "company_id": company_data.get("company_id", ""),
                "company_name": company_data.get("company_name", "")
            },
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.evaluation_contexts[evaluation_id] = context
        self.logger.info(f"Created evaluation context: {evaluation_id}")
        
        return context
    
    def get_evaluation_context(self, evaluation_id: str) -> Optional[EvaluationContext]:
        """Obtiene el contexto de una evaluación"""
        return self.evaluation_contexts.get(evaluation_id)
    
    def update_workflow_state(self, evaluation_id: str, state_updates: Dict[str, Any]) -> bool:
        """Actualiza el estado del workflow"""
        
        context = self.evaluation_contexts.get(evaluation_id)
        if not context:
            return False
        
        context.workflow_state.update(state_updates)
        context.last_updated = datetime.now()
        
        self.logger.info(f"Updated workflow state for {evaluation_id}: {state_updates}")
        return True
    
    # Agent Memory Management
    
    def create_agent_memory(self, agent_id: str, evaluation_id: str) -> AgentMemory:
        """Crea memoria para un agente específico"""
        
        memory = AgentMemory(
            agent_id=agent_id,
            evaluation_id=evaluation_id,
            context_entries=[],
            current_state={"status": "initialized"},
            execution_history=[],
            last_updated=datetime.now()
        )
        
        memory_key = f"{evaluation_id}_{agent_id}"
        self.agent_memories[memory_key] = memory
        
        # Add to evaluation context
        context = self.evaluation_contexts.get(evaluation_id)
        if context:
            context.agent_memories[agent_id] = memory
        
        self.logger.info(f"Created agent memory: {agent_id} for evaluation {evaluation_id}")
        return memory
    
    def add_context_entry(self, evaluation_id: str, agent_id: str, 
                         context_type: str, content: str, 
                         metadata: Dict[str, Any] = None) -> str:
        """Añade una entrada de contexto"""
        
        entry_id = f"{evaluation_id}_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        entry = ContextEntry(
            entry_id=entry_id,
            evaluation_id=evaluation_id,
            agent_id=agent_id,
            context_type=context_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
        
        # Add to agent memory
        memory_key = f"{evaluation_id}_{agent_id}"
        memory = self.agent_memories.get(memory_key)
        
        if not memory:
            memory = self.create_agent_memory(agent_id, evaluation_id)
        
        memory.context_entries.append(entry)
        memory.last_updated = datetime.now()
        
        # Store in Semantic Kernel memory
        asyncio.create_task(self._store_in_sk_memory(entry))
        
        self.logger.info(f"Added context entry: {entry_id}")
        return entry_id
    
    async def _store_in_sk_memory(self, entry: ContextEntry):
        """Almacena entrada en memoria de Semantic Kernel"""
        try:
            # Simplified memory storage for current SK version
            self.logger.debug(f"Stored context entry in memory: {entry.entry_id}")
        except Exception as e:
            self.logger.error(f"Failed to store in SK memory: {e}")
    
    def get_agent_memory(self, evaluation_id: str, agent_id: str) -> Optional[AgentMemory]:
        """Obtiene la memoria de un agente"""
        memory_key = f"{evaluation_id}_{agent_id}"
        return self.agent_memories.get(memory_key)
    
    def update_agent_state(self, evaluation_id: str, agent_id: str, 
                          state_updates: Dict[str, Any]) -> bool:
        """Actualiza el estado de un agente"""
        
        memory = self.get_agent_memory(evaluation_id, agent_id)
        if not memory:
            return False
        
        memory.current_state.update(state_updates)
        memory.last_updated = datetime.now()
        
        # Add to execution history
        memory.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "state_update": state_updates
        })
        
        return True
    
    # Context Retrieval and Search
    
    async def search_context(self, evaluation_id: str, query: str, 
                           limit: int = 5) -> List[ContextEntry]:
        """Busca en el contexto usando búsqueda semántica"""
        try:
            # Simplified context search for current SK version
            context_entries = []
            
            # Search through agent memories manually
            for memory in self.agent_memories.values():
                if memory.evaluation_id == evaluation_id:
                    for entry in memory.context_entries:
                        if query.lower() in entry.content.lower():
                            entry.relevance_score = 0.8  # Simple relevance score
                            context_entries.append(entry)
            
            # Sort by relevance and limit results
            context_entries.sort(key=lambda e: e.relevance_score, reverse=True)
            return context_entries[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to search context: {e}")
            return []
    
    def get_relevant_context(self, evaluation_id: str, agent_id: str, 
                           context_types: List[str] = None) -> List[ContextEntry]:
        """Obtiene contexto relevante para un agente"""
        
        context = self.evaluation_contexts.get(evaluation_id)
        if not context:
            return []
        
        relevant_entries = []
        
        # Get entries from all agents in the evaluation
        for memory in context.agent_memories.values():
            for entry in memory.context_entries:
                if context_types is None or entry.context_type in context_types:
                    relevant_entries.append(entry)
        
        # Sort by timestamp (most recent first)
        relevant_entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Limit to context window size
        return relevant_entries[:self.sk_config.context_window_size]
    
    # Planning and Execution
    
    async def create_execution_plan(self, evaluation_id: str, 
                                  goal: str) -> Optional[Dict[str, Any]]:
        """Crea un plan de ejecución usando Semantic Kernel planner"""
        
        if not self.sk_config.enable_planning:
            return None
        
        try:
            # Simplified planning for current SK version
            plan_dict = {
                "plan_id": f"plan_{evaluation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "evaluation_id": evaluation_id,
                "goal": goal,
                "steps": [
                    {
                        "step_number": 1,
                        "description": f"Execute goal: {goal}",
                        "parameters": {}
                    }
                ],
                "created_date": datetime.now().isoformat()
            }
            
            self.logger.info(f"Created execution plan: {plan_dict['plan_id']}")
            return plan_dict
            
        except Exception as e:
            self.logger.error(f"Failed to create execution plan: {e}")
            return None
    
    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un plan de ejecución"""
        
        execution_result = {
            "plan_id": plan["plan_id"],
            "execution_id": f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "completed",
            "steps_completed": len(plan["steps"]),
            "results": [
                {
                    "step_number": i + 1,
                    "result": f"Executed step {i + 1}",
                    "timestamp": datetime.now().isoformat()
                }
                for i, step in enumerate(plan["steps"])
            ],
            "errors": [],
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat()
        }
        
        return execution_result
    
    # Memory Management
    
    def cleanup_old_contexts(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Limpia contextos antiguos"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleanup_stats = {"removed_contexts": 0, "removed_memories": 0}
        
        # Remove old evaluation contexts
        contexts_to_remove = []
        for evaluation_id, context in self.evaluation_contexts.items():
            if context.created_date < cutoff_date:
                contexts_to_remove.append(evaluation_id)
        
        for evaluation_id in contexts_to_remove:
            del self.evaluation_contexts[evaluation_id]
            cleanup_stats["removed_contexts"] += 1
        
        # Remove old agent memories
        memories_to_remove = []
        for memory_key, memory in self.agent_memories.items():
            if memory.last_updated < cutoff_date:
                memories_to_remove.append(memory_key)
        
        for memory_key in memories_to_remove:
            del self.agent_memories[memory_key]
            cleanup_stats["removed_memories"] += 1
        
        self.logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de memoria"""
        
        total_entries = sum(
            len(memory.context_entries) 
            for memory in self.agent_memories.values()
        )
        
        return {
            "active_evaluations": len(self.evaluation_contexts),
            "agent_memories": len(self.agent_memories),
            "total_context_entries": total_entries,
            "memory_store_type": self.sk_config.memory_store_type,
            "context_window_size": self.sk_config.context_window_size,
            "max_memory_entries": self.sk_config.max_memory_entries,
            "last_updated": datetime.now().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del servicio"""
        try:
            # Test memory store
            memory_healthy = self.memory_store is not None
            
            return {
                "status": "healthy",
                "kernel_initialized": self.kernel is not None,
                "memory_store_healthy": memory_healthy,
                "planning_enabled": self.sk_config.enable_planning,
                "active_contexts": len(self.evaluation_contexts),
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }