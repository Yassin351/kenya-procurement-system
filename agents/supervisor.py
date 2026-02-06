from typing import Dict, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from core.logging import get_logger
from core.models import SystemState
from core.monitoring import (
    get_system_monitor, 
    CircuitBreaker, 
    TimeoutError as MonitoringTimeoutError,
    max_iterations
)
from agents.market_agent import market_agent
from agents.price_agent import price_agent
from agents.compliance_agent import compliance_agent

logger = get_logger('supervisor')
monitor = get_system_monitor()

# Configuration
MAX_WORKFLOW_ITERATIONS = 100
WORKFLOW_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_RETRIES_PER_STEP = 3

# Circuit breaker for entire workflow
workflow_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=180,
    expected_exception=Exception
)


class SupervisorAgent:
    """Supervisor agent orchestrating multi-agent workflow with resilience."""
    
    def __init__(self):
        self.app = self._build_graph()
        self.workflow_start_time = None
        logger.info('Supervisor initialized with resilience features')
    
    def _build_graph(self):
        """Build LangGraph workflow with proper node wrapping."""
        workflow = StateGraph(dict)
        
        # Add wrapped nodes with error handling
        workflow.add_node('market', self._safe_node_wrapper('market', market_agent))
        workflow.add_node('price', self._safe_node_wrapper('price', price_agent))
        workflow.add_node('compliance', self._safe_node_wrapper('compliance', compliance_agent))
        
        workflow.set_entry_point('market')
        workflow.add_edge('market', 'price')
        workflow.add_edge('price', 'compliance')
        workflow.add_edge('compliance', END)
        
        return workflow.compile()
    
    def _safe_node_wrapper(self, node_name: str, agent_func):
        """Wrap agent function with error handling and monitoring."""
        def wrapped_agent(state: dict) -> dict:
            start_time = datetime.now()
            
            try:
                # Check workflow timeout
                if self.workflow_start_time:
                    elapsed = (datetime.now() - self.workflow_start_time).total_seconds()
                    if elapsed > WORKFLOW_TIMEOUT_SECONDS:
                        logger.error(f"Workflow timeout exceeded ({elapsed}s > {WORKFLOW_TIMEOUT_SECONDS}s)")
                        error_msg = f"Workflow timeout at {node_name}"
                        state['errors'] = state.get('errors', []) + [error_msg]
                        state['step'] = 'workflow_timeout'
                        return state
                
                logger.info(f"Executing node: {node_name}")
                result = agent_func(state)
                
                # Record metrics
                response_time = (datetime.now() - start_time).total_seconds()
                monitor.record_request(f'node_{node_name}', response_time)
                logger.info(f"Node {node_name} completed in {response_time:.2f}s")
                
                return result
            
            except Exception as e:
                logger.error(f"Node {node_name} failed: {str(e)}")
                monitor.record_error(f'node_{node_name}_failure', str(e))
                
                # Add error to state and continue
                state['errors'] = state.get('errors', []) + [f"{node_name}: {str(e)}"]
                state['step'] = f'{node_name}_failed'
                
                return state
        
        return wrapped_agent
    
    def run(self, query: str, category: str = 'general', catalog_path: Optional[str] = None) -> Dict:
        """
        Run procurement workflow with resilience and monitoring.
        
        Args:
            query: Product search query
            category: Product category
            catalog_path: Optional path to supplier catalog
        
        Returns:
            Workflow result dictionary
        """
        self.workflow_start_time = datetime.now()
        
        try:
            initial_state = {
                'query': query,
                'product_category': category,
                'collected_data': {'catalog_path': catalog_path} if catalog_path else {},
                'market_data': [],
                'price_analysis': {},
                'compliance_checks': {},
                'final_recommendation': {},
                'errors': [],
                'retry_count': 0,
                'step': 'initialized',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f'Starting resilient workflow for: {query} (category: {category})')
            
            # Run through circuit breaker
            result = workflow_circuit_breaker.call(
                self.app.invoke,
                initial_state
            )
            
            # Record overall workflow metrics
            total_time = (datetime.now() - self.workflow_start_time).total_seconds()
            
            # Add timing info
            result['execution_time_seconds'] = total_time
            result['completed_at'] = datetime.now().isoformat()
            
            # Log completion
            error_count = len(result.get('errors', []))
            if error_count == 0:
                logger.info(f'Workflow completed successfully in {total_time:.2f}s')
                monitor.record_request('workflow_complete_success', total_time)
            else:
                logger.warning(f'Workflow completed with {error_count} errors in {total_time:.2f}s')
                monitor.record_error('workflow_completed_with_errors', f'{error_count} errors')
            
            return result
        
        except Exception as e:
            logger.critical(f'Workflow execution failed: {str(e)}')
            monitor.record_error('workflow_failure', str(e))
            
            # Return graceful failure response
            return {
                'query': query,
                'product_category': category,
                'errors': [str(e)],
                'market_data': [],
                'price_analysis': {},
                'compliance_checks': {},
                'final_recommendation': {},
                'step': 'workflow_failed',
                'execution_time_seconds': (datetime.now() - self.workflow_start_time).total_seconds(),
                'completed_at': datetime.now().isoformat()
            }


_supervisor = None


def get_supervisor() -> SupervisorAgent:
    """Get or create global supervisor instance."""
    global _supervisor
    if _supervisor is None:
        _supervisor = SupervisorAgent()
    return _supervisor


def run_procurement(query: str, category: str = 'general', catalog_path: Optional[str] = None) -> Dict:
    """
    Public API for running procurement workflow.
    
    Args:
        query: Product search query
        category: Product category
        catalog_path: Optional path to supplier catalog
    
    Returns:
        Workflow result with market data, price analysis, and compliance checks
    """
    supervisor = get_supervisor()
    return supervisor.run(query, category, catalog_path)

def run_procurement(query: str, category: str = 'general', catalog_path: str = None) -> Dict:
    return get_supervisor().run(query, category, catalog_path)
