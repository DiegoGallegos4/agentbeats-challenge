import re
from typing import TypedDict, Annotated, List, Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage

# Import agents
from .agents import (
    market_agent, options_agent, insider_agent, 
    news_agent, web_agent, website_agent, analyst_agent,
    quant_agent
)

class TickerState(TypedDict):
    ticker: str
    date: str # Optional target date
    scores: Dict[str, float]
    analyses: Dict[str, str]
    errors: List[str]

def parse_score(output: str) -> float:
    """Extracts score from agent output."""
    try:
        # Match "Score: 0.5", "**Score**: 0.5", "Score: +0.5", etc.
        match = re.search(r"Score\**:\s*([-+]?\d*\.?\d+)", output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.0
    except Exception:
        return 0.0

def create_node(agent, name, custom_prompt_func=None):
    def node_func(state: TickerState):
        ticker = state['ticker']
        date = state.get('date')
        
        if custom_prompt_func:
            prompt = custom_prompt_func(ticker, date)
        else:
            prompt = f"Analyze {ticker}"
            if date:
                prompt += f" as of {date}"
            prompt += "\nIMPORTANT: You MUST conclude with 'Score: X.X' where X.X is between -1.0 and 1.0."
            
        try:
            response = agent.invoke({"messages": [HumanMessage(content=prompt)]})
            # response is a dict with 'messages'
            output = response['messages'][-1].content
            score = parse_score(output)
            
            return {
                "scores": {name: score},
                "analyses": {name: output}
            }
        except Exception as e:
            return {
                "errors": [f"{name} failed: {str(e)}"],
                "scores": {name: 0.0} # Default to neutral on error
            }
    return node_func

# Define Nodes
market_node = create_node(market_agent, "market")
options_node = create_node(options_agent, "options")
insider_node = create_node(insider_agent, "insider")
news_node = create_node(news_agent, "news")
web_node = create_node(web_agent, "web")
def website_prompt(ticker, date):
    p = f"Find and analyze the Investor Relations page for {ticker}"
    if date:
        p += f" looking for updates around {date}"
    p += "\nIMPORTANT: You MUST conclude with 'Score: X.X' where X.X is between -1.0 and 1.0."
    return p

website_node = create_node(website_agent, "website", custom_prompt_func=website_prompt)
analyst_node = create_node(analyst_agent, "analyst")
quant_node = create_node(quant_agent, "quant")
# ... (Aggregator and StateGraph definition) ...

def aggregator(state: TickerState):
    # This node is just a synchronization point
    return state

import operator
from typing import Union

def update_dict(a: Dict, b: Dict) -> Dict:
    a.update(b)
    return a

def update_list(a: List, b: List) -> List:
    return a + b

class TickerStateMerged(TypedDict):
    ticker: str
    date: str
    scores: Annotated[Dict[str, float], update_dict]
    analyses: Annotated[Dict[str, str], update_dict]
    errors: Annotated[List[str], update_list]

workflow = StateGraph(TickerStateMerged)

# Add Nodes
workflow.add_node("market", market_node)
workflow.add_node("options", options_node)
workflow.add_node("insider", insider_node)
workflow.add_node("news", news_node)
workflow.add_node("web", web_node)
workflow.add_node("website", website_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("quant", quant_node)
workflow.add_node("aggregator", aggregator)

def start_node(state):
    return state

workflow.add_node("start", start_node)
workflow.set_entry_point("start")

# Define Edges
# ...
workflow.add_edge("start", "market")
workflow.add_edge("start", "options")
workflow.add_edge("start", "insider")
workflow.add_edge("start", "news")
workflow.add_edge("start", "web")
workflow.add_edge("start", "website")
workflow.add_edge("start", "analyst")
workflow.add_edge("start", "quant")

# All agents to aggregator
workflow.add_edge("market", "aggregator")
workflow.add_edge("options", "aggregator")
workflow.add_edge("insider", "aggregator")
workflow.add_edge("news", "aggregator")
workflow.add_edge("web", "aggregator")
workflow.add_edge("website", "aggregator")
workflow.add_edge("analyst", "aggregator")
workflow.add_edge("quant", "aggregator")

workflow.add_edge("aggregator", END)

app = workflow.compile()
