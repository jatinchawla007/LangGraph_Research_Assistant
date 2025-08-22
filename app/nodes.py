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

# --- FINAL, DEBUGGED PLANNER NODE ---
def generate_research_plan(state: GraphState) -> dict:
    """
    Generates a research plan. If it's a follow-up, it first rewrites the
    topic to be self-contained based on the conversation history.
    """
    print("--- 🧠 Generating Research Plan ---")
    topic = state["topic"]
    context = state.get("context_summary", "")

    # The planner will always use the powerful model
    planner = smart_llm.with_structured_output(ResearchPlan)
    
    # If context exists, we first create a standalone topic
    if context:
        # This print statement is our key debugging check
        print("--- Rewriting topic with context ---")
        
        rewriter_prompt = f"""You are an expert at rewriting a user's follow-up question to be a standalone question. Understand the intent of the follow-up question and then only proceed.
        
        Use the provided conversation history to understand the context, and rewrite the follow-up question to be a complete question that doesn't require the history to be understood. List all the specific names or entities in the standalone question to make it understandable on its own. Do not output any extra commentary or statements.
        Conversation History:
        ---
        {context}
        ---

        Follow-up Question: "{topic}"

        Standalone Question:
        """
        
        standalone_topic_message = smart_llm.invoke(rewriter_prompt)
        standalone_topic = standalone_topic_message.content

        # This new print statement will show us the exact topic being sent to the planner
        print(f"--- Standalone Topic: {standalone_topic} ---")
        
        # Create the prompt for the main planner using the new topic
        prompt = f"""As a professional research assistant, create a detailed and actionable research plan for the following topic: '{standalone_topic}'.

The user has provided this topic as a follow-up to a previous conversation. Ensure your new plan is highly relevant and builds directly on this context. Do not suggest questions or search queries that are too generic.
Your plan must include:
1. A list of 3 specific research questions that need to be answered.
2. A list of 3 search engine queries that will be used to find relevant information.
Adhere to the guidelines and do not output any additional text or explanations.

"""
    else:
        # The original prompt for non-follow-up questions
        prompt = f"""As a professional research assistant, create a detailed and actionable research plan for the following topic: '{topic}'.
    
Your plan must include:
1. A list of 3 specific research questions that need to be answered.
2. A list of 3 search engine queries that will be used to find relevant information.
Adhere to the guidelines and do not output any additional text or explanations.
"""

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

    prompt = f"""Based on the user's previous research briefs, provide a concise, one-paragraph summary of their key findings. This summary will be used as context for their new research query. Maintain all the important details and nuances.

Here is the user's past research history:
{formatted_history}
"""
    
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