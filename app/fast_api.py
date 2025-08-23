# app/main.py

from fastapi import FastAPI
from .schemas import BriefRequest, FinalBrief
from .database import init_db, save_brief
from .graph_state import GraphState
from langgraph.graph import StateGraph

# Import all your node and utility functions
from .nodes import (
    entry_point,
    route_to_context_or_planner,
    summarize_context,
    generate_research_plan,
    perform_web_search,
    fetch_and_summarize_content,
    generate_final_brief,
)

# This function builds our LangGraph app. We'll call it once on startup.
def build_graph():
    """Builds the LangGraph workflow with conditional routing."""
    workflow = StateGraph(GraphState)
    workflow.add_node("entry_point", entry_point)
    workflow.add_node("summarize_context", summarize_context)
    workflow.add_node("planner", generate_research_plan)
    workflow.add_node("searcher", perform_web_search)
    workflow.add_node("summarizer", fetch_and_summarize_content)
    workflow.add_node("synthesizer", generate_final_brief)
    
    workflow.set_entry_point("entry_point")
    workflow.add_conditional_edges(
        "entry_point",
        route_to_context_or_planner,
        {"summarize_context": "summarize_context", "planner": "planner"},
    )
    workflow.add_edge("summarize_context", "planner")
    workflow.add_edge("planner", "searcher")
    workflow.add_edge("searcher", "summarizer")
    workflow.add_edge("summarizer", "synthesizer")
    workflow.set_finish_point("synthesizer")
    
    return workflow.compile()

# --- Learning Point: Application Lifecycle ---
# We build the graph once when the application starts up.
# This is much more efficient than rebuilding it for every single request.
# The `research_graph` object is then reused for all incoming API calls.
init_db()
research_graph = build_graph()

# Create the FastAPI application instance
app = FastAPI(
    title="AI Research Assistant API",
    description="An API for generating research briefs with contextual memory.",
    version="1.0.0",
)

@app.post("/brief", response_model=FinalBrief)
async def create_research_brief(request: BriefRequest):
    """
    Receives a research topic and returns a structured brief.
    """
    print(f"Received request for user '{request.user_id}' on topic: '{request.topic}'")

    # Construct the input for the graph
    inputs = {
        "user_id": request.user_id,
        "topic": request.topic,
        "follow_up": request.follow_up,
        "search_depth": request.search_depth
    }

   
    final_state = research_graph.invoke(inputs)
    brief = final_state.get("final_brief")

    if brief:
        # Save the successful brief to the database for future context
        save_brief(request.user_id, brief)
        return brief
    else:
        # Handle cases where the graph might fail to produce a brief
        return {"error": "Failed to generate a research brief."}

@app.get("/")
def read_root():
    return {"status": "Research Assistant API is running."}