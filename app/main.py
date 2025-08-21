# app/main.py
from langgraph.graph import StateGraph
from .graph_state import GraphState
from .nodes import generate_research_plan, perform_web_search, fetch_and_summarize_content, generate_final_brief




def build_graph():
    """Builds the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("planner", generate_research_plan)
    workflow.add_node("web_search", perform_web_search)
    workflow.add_node("summarize_sources", fetch_and_summarize_content)
    workflow.add_node("generate_final_brief", generate_final_brief)

    # Set the entrypoint
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "web_search")
    workflow.add_edge("web_search", "summarize_sources")
    workflow.add_edge("summarize_sources", "generate_final_brief")

    # Set the finish point
    workflow.set_finish_point("generate_final_brief")

    # Compile the graph into a runnable app
    app = workflow.compile()
    return app



if __name__ == "__main__":
    app = build_graph()

    topic = input("Enter the research topic: ")
    inputs = {"topic": topic}

    # Run the graph and get the final state
    final_state = app.invoke(inputs)

    # Extract the final brief from the state
    brief = final_state.get("final_brief")

    if brief:
        print("\n" + "="*80)
        print(f"\n## Research Brief: {brief.topic}\n")
        print("="*80)
        
        print("\n### Introduction\n")
        print(brief.introduction)
        
        print("\n### Synthesis\n")
        print(brief.synthesis)
        
        print("\n### Potential Follow-up Questions\n")
        for i, question in enumerate(brief.potential_follow_ups, 1):
            print(f"{i}. {question}")
            
        print("\n### References\n")
        for i, ref in enumerate(brief.references, 1):
            print(f"{i}. [{ref.title}]({ref.url})")
            
        print("\n" + "="*80)