from agent.purple.agents import web_agent
from langchain_core.messages import HumanMessage

def test_web_agent(ticker, date):
    print(f"--- Testing Web Agent for {ticker} as of {date} ---")
    # Using the same prompt logic as in graph.py
    prompt = f"Analyze {ticker} as of {date}\nIMPORTANT: You MUST conclude with 'Score: X.X' where X.X is between -1.0 and 1.0."
    try:
        response = web_agent.invoke({"messages": [HumanMessage(content=prompt)]})
        output = response['messages'][-1].content
        print(f"Output:\n{output}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test for a few tickers
    test_web_agent("AAPL", "2025-12-22")
    test_web_agent("TSLA", "2025-12-22")
