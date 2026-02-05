from langgraph.graph import StateGraph, END

def create_procurement_graph():
    from agents.market_agent import market_agent
    from agents.price_agent import price_agent
    from agents.compliance_agent import compliance_agent
    
    workflow = StateGraph(dict)
    workflow.add_node("market", market_agent)
    workflow.add_node("price", price_agent)
    workflow.add_node("compliance", compliance_agent)
    workflow.set_entry_point("market")
    workflow.add_edge("market", "price")
    workflow.add_edge("price", "compliance")
    workflow.add_edge("compliance", END)
    return workflow.compile()
