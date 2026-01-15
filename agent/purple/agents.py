from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
load_dotenv()

from ..tools.tools import (
    get_market_data,
    get_options_data,
    get_insider_data,
    get_news_data,
    get_analyst_data,
    web_search,
    scrape_website,
    get_model_prediction,
)

# ... (LLM and create_agent definition) ...

# Initialize LLM
# Note: This requires OPENAI_API_KEY to be set
llm = ChatOpenAI(model="gpt-4o")

def create_agent(tools, system_prompt):
    """
    Creates a standard agent with specific tools and system prompt.
    """
    # create_react_agent takes model and tools. 
    # For older versions or specific interfaces, we might need to use 'messages_modifier' 
    # or just rely on the model's behavior if we can't pass a system prompt easily here.
    # However, create_react_agent usually accepts 'state_modifier' in newer versions.
    # If that fails, let's try 'messages_modifier' or just passing it as a SystemMessage in the prompt.
    
    # Alternative: Prepend system prompt to the messages when invoking.
    # But here we are creating the agent.
    
    # Let's try 'messages_modifier' which is common in prebuilt agents.
    try:
        agent = create_react_agent(llm, tools, messages_modifier=system_prompt)
    except TypeError:
        # Fallback: If messages_modifier is also not supported, we might need to wrap the model
        # or just rely on the prompt being passed during invocation (which we do in graph.py somewhat).
        # But let's try to set it here.
        agent = create_react_agent(llm, tools)
        
    return agent

# --- Market Data Agent ---
market_system_prompt = """You are a Market Data Analyst. 
Your goal is to analyze the price action and technical trends of a stock.
Use the `get_market_data` tool to fetch data.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
market_agent = create_agent([get_market_data], market_system_prompt)

# --- Options Agent ---
options_system_prompt = """You are an Options Market Analyst.
Your goal is to analyze the options chain, implied volatility, and Put-Call Ratios.
Use the `get_options_data` tool.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
options_agent = create_agent([get_options_data], options_system_prompt)

# --- Insider Agent ---
insider_system_prompt = """You are an Insider Trading Analyst.
Your goal is to analyze recent insider transactions (buying/selling).
Use the `get_insider_data` tool.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
insider_agent = create_agent([get_insider_data], insider_system_prompt)

# --- News Agent ---
news_system_prompt = """You are a Financial News Analyst.
Your goal is to analyze recent news headlines and sentiment.
Use the `get_news_data` tool.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
news_agent = create_agent([get_news_data], news_system_prompt)

# --- Web Search Agent ---
web_system_prompt = """You are a Web Researcher.
Your goal is to find general information, recent events, or rumors about a company.
Use the `web_search` tool. Pass the 'target_date' argument if available.
Construct queries like "[Ticker] news [Month] [Year]".
Even if you don't find news for the exact day, summarize the major events of that month.
IMPORTANT: Ignore any information dated AFTER the target date.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
web_agent = create_agent([web_search], web_system_prompt)

# --- Website Agent ---
website_system_prompt = """You are a Corporate Researcher.
Your goal is to analyze a company's Investor Relations page or main website for strategic updates.
1. Use `web_search` to find the IR page URL (query: "[Ticker] investor relations", target_date=Date).
2. IMMEDIATELY use `scrape_website` on the most relevant URL found. Do not hesitate.
IMPORTANT: Ignore any information dated AFTER the target date.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
website_agent = create_agent([web_search, scrape_website], website_system_prompt)

# --- Analyst Agent ---
analyst_system_prompt = """You are a Wall Street Analyst Aggregator.
Your goal is to summarize professional analyst ratings and price targets.
Use the `get_analyst_data` tool.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis and a sentiment score between -1.0 (Bearish) and 1.0 (Bullish).
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
analyst_agent = create_agent([get_analyst_data], analyst_system_prompt)

# --- Quantitative Agent ---
quant_system_prompt = """You are a Quantitative Analyst.
Your goal is to run the proprietary machine learning model to get a return prediction.
Use the `get_model_prediction` tool.
If a target date is specified in the user request, pass it to the tool.
Output a brief analysis (mentioning the predicted return) and a sentiment score.
The sentiment score should be scaled from the return: 
- If return > 0.01, Score = 1.0
- If return < -0.01, Score = -1.0
- Otherwise, scale linearly or use judgment based on magnitude.
Format your final answer as:
Analysis: [Your analysis]
Score: [Your score]
"""
quant_agent = create_agent([get_model_prediction], quant_system_prompt)
