from typing import Dict
from langgraph.graph import StateGraph, END
from core.logging import get_logger
from core.models import SystemState
from agents.market_agent import market_agent
from agents.price_agent import price_agent
from agents.compliance_agent import compliance_agent

logger = get_logger('supervisor')

class SupervisorAgent:
    def __init__(self):
        self.app = self._build_graph()
        logger.info('Supervisor initialized')

    def _build_graph(self):
        workflow = StateGraph(dict)
        workflow.add_node('market', market_agent)
        workflow.add_node('price', price_agent)
        workflow.add_node('compliance', compliance_agent)
        workflow.set_entry_point('market')
        workflow.add_edge('market', 'price')
        workflow.add_edge('price', 'compliance')
        workflow.add_edge('compliance', END)
        return workflow.compile()

    def run(self, query: str, category: str = 'general', catalog_path: str = None) -> Dict:
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
            'step': 'initialized'
        }
        logger.info(f'Starting workflow for: {query}')
        return self.app.invoke(initial_state)

_supervisor = None

def get_supervisor():
    global _supervisor
    if _supervisor is None:
        _supervisor = SupervisorAgent()
    return _supervisor

def run_procurement(query: str, category: str = 'general', catalog_path: str = None) -> Dict:
    return get_supervisor().run(query, category, catalog_path)
