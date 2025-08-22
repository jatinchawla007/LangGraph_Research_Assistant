# app/nodes.py

from .graph_state import GraphState
from .llm import smart_llm, tavily_tool, fast_llm, tavily_client
from .schemas import ResearchPlan, SourceSummary, FinalBrief
from .database import get_briefs_by_user

from langchain_community.document_loaders import WebBaseLoader
import pprint
import json

def entry_point(state: GraphState) -> dict:
    """
    A dummy node that just starts the graph and does nothing to the state.
    This is the entry point from which our conditional routing will branch.
    """
    print("--- 🚀 Starting Research Graph ---")
    return {} # Must return a dictionary, even if it's empty

def generate_research_plan(state: GraphState) -> dict:
    """
    Generates a research plan based on the user's topic and conversation history.
    """
    print("--- 🧠 Generating Research Plan ---")
    topic = state["topic"]
    context = state.get("context_summary", "") # Use .get() for safety

    planner = smart_llm.with_structured_output(ResearchPlan)

    # --- Learning Point: Context-Aware Prompting ---
    # We now check if there's a context summary. If so, we use a more
    # sophisticated prompt that instructs the LLM to consider the past
    # conversation, leading to more relevant and non-repetitive research plans.
    if context:
        prompt = f"""As a professional research assistant, create a detailed and actionable research plan for the following topic: '{topic}'.

Please consider the following summary of our previous conversation as crucial context. Ensure your new plan builds upon or explores different angles from the previous research, and does not repeat questions or search queries that have already been addressed.

Previous conversation summary:
---
{context}

As a professional research assistant, create a detailed and actionable research plan for the following topic: '{topic}'.
    
    Your plan must include:
    1. A list of 3 specific research questions that need to be answered.
    2. A list of 3 search engine queries that will be used to find relevant information.
    
    Ensure the plan is comprehensive and directly addresses the user's topic."""

    else:
        prompt = f"""As a professional research assistant, create a detailed and actionable research plan for the following topic: '{topic}'.
    
    Your plan must include:
    1. A list of 3 specific research questions that need to be answered.
    2. A list of 3 search engine queries that will be used to find relevant information.
    
    Ensure the plan is comprehensive and directly addresses the user's topic."""


    plan = planner.invoke(prompt)
    return {"research_plan": plan}


# --- New Node ---
def perform_web_search(state: GraphState) -> dict:
    """
    Performs web searches using the direct Tavily client to ensure structured output.
    """
    print("--- 🔍 Performing Web Search (Direct Client) ---")
    research_plan = state["research_plan"]
    if not research_plan:
        return {}

    all_results = []
    for query in research_plan.search_queries:
        print(f"Searching for: '{query}'")
        try:
            response = tavily_client.search(query=query, search_depth="basic", max_results=2)
            all_results.extend(response['results'])
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            
    return {"search_results": all_results}

def fetch_and_summarize_content(state: GraphState) -> dict:
    """
    Fetches content from URLs using WebBaseLoader and generates a summary for each.
    """
    print("--- 📚 Fetching and Summarizing Content ---")
    topic = state["topic"]
    search_results = state["search_results"]
    if not search_results:
        return {}

    summarizer = fast_llm.with_structured_output(SourceSummary)
    
    all_summaries = []
    for result in search_results:
        url = result.get("url")
        if not url:
            continue
        
        print(f"Fetching and summarizing: {url}")
        try:
            loader = WebBaseLoader([url])
            docs = loader.load()
            text_content = docs[0].page_content if docs else ""

            if not text_content:
                continue

            prompt = f"""Your task is to create a structured summary of the following text, which was extracted from the URL {url}. The research is for the topic: '{topic}'.

Please generate a JSON object that strictly follows this schema:
- "url": The original URL of the source.
- "title": The title of the web page.
- "key_points": A list of 3-5 key takeaways from the text as strings.
- "relevance_to_topic": A brief explanation of why this text is relevant to the main topic '{topic}'.
- "relevance_score": A score between 0 and 1 indicating the relevance of the text to the topic.
- Do not return any additional text or explanations. For eg "Here is the summary:". Just return the JSON object.
- Do not even return <tool-use> XML tags.

Here is the text to summarize:
---
{text_content[:5000]}
---
"""
            summary_object = summarizer.invoke(prompt)
            all_summaries.append(summary_object)
        except Exception as e:
            pprint.pprint(f"Error processing {url}: {e}")

    return {"source_summaries": all_summaries}

def generate_final_brief(state: GraphState) -> dict:
    """
    Synthesizes the collected summaries into a final research brief.
    """
    print("--- ✍️ Synthesizing Final Brief ---")
    topic = state["topic"]
    summaries = state["source_summaries"]

    if not summaries:
        return {"final_brief": "Error: No summaries to synthesize."}

    synthesizer = smart_llm.with_structured_output(FinalBrief)

    # Convert the list of Pydantic objects to a JSON string for the prompt
    summaries_json_str = json.dumps([s.dict() for s in summaries], indent=2)

    prompt = f"""As a senior research analyst, your task is to produce a comprehensive research brief on the topic: "{topic}".

You have been provided with a list of structured summaries from various web sources. Your job is to synthesize this information into a single, coherent, and well-structured report.

The final brief must follow the `FinalBrief` schema and include:
- "topic": The original research topic.
- "introduction": A brief, engaging introduction to the topic.
- "synthesis": A highly detailed synthesis of the information from the provided summaries. This should be the main body of the brief, combining insights and answering the core research questions. Make sure to highlight any areas of consensus or disagreement among the sources.
- "references": A list of the source summaries you used.
- "potential_follow_ups": A list of 2-3 relevant follow-up questions or areas for future research.

Here are the source summaries in JSON format:
---
{summaries_json_str}
---
"""

    final_brief = synthesizer.invoke(prompt)
    
    return {"final_brief": final_brief}


# --- NEW MEMORY NODE ---
def summarize_context(state: GraphState) -> dict:
    """
    Summarizes the user's past research briefs to provide context for the new query.
    """
    print("---📝 Summarizing Context---")
    user_id = state["user_id"]
    
    past_briefs = get_briefs_by_user(user_id)
    
    if not past_briefs:
        print("No past briefs found for this user.")
        return {"context_summary": ""}

    # Format the past briefs for the LLM prompt
    formatted_history = "\n\n---\n\n".join(
        [f"Topic: {b.topic}\nIntroduction: {b.introduction}" for b in past_briefs]
    )

    prompt = f"""Based on the user's previous research briefs, provide a concise, one-paragraph summary of their past interests and key findings. This summary will be used as context for their new research query.

Here is the user's past research history:
{formatted_history}
"""
    
    # --- Learning Point: Reusing LLMs ---
    # Context summarization is a quick, factual task, making it a
    # perfect use case for our efficient `fast_llm`.
    summary_message = fast_llm.invoke(prompt)
    
    summary = summary_message.content
    print(f"Generated Context Summary: {summary}")

    return {"context_summary": summary}


# --- NEW ROUTER NODE ---
def route_to_context_or_planner(state: GraphState) -> str:
    """
    A router to decide whether to summarize context or go straight to planning.

    Args:
        state: The current graph state.

    Returns:
        A string indicating the next node to execute.
    """
    print("--- 🚦 Routing ---")
    if state["follow_up"]:
        print("Follow-up detected, routing to context summarizer.")
        return "summarize_context"
    else:
        print("No follow-up, routing directly to planner.")
        return "planner"