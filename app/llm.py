# app/llms.py

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from tavily import TavilyClient

# Load environment variables from the .env file
load_dotenv()
os.environ['USER_AGENT'] = 'myagent'


fast_llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.2,
)

# For more complex tasks like synthesizing the final brief, a more powerful
# model might be better. We can define it here for later use.
smart_llm = ChatGroq(
    model_name="deepseek-r1-distill-llama-70b",
    temperature=0.6,
)

tavily_tool = TavilySearch(max_results=3)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))