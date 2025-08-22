# app/main.py
from langgraph.graph import StateGraph
from .graph_state import GraphState
from .nodes import generate_research_plan, perform_web_search, fetch_and_summarize_content, generate_final_brief, route_to_context_or_planner, summarize_context, entry_point
from .database import init_db, save_brief 



def build_graph():
    """Builds the LangGraph workflow with conditional routing."""
    workflow = StateGraph(GraphState)

    # Add all the state-modifying nodes
    workflow.add_node("entry_point", entry_point) # <-- Add the new entry node
    workflow.add_node("summarize_context", summarize_context)
    workflow.add_node("planner", generate_research_plan)
    workflow.add_node("searcher", perform_web_search)
    workflow.add_node("summarizer", fetch_and_summarize_content)
    workflow.add_node("synthesizer", generate_final_brief)
    
    # NOTE: We DO NOT add the 'route_to_context_or_planner' as a node.
    # It is only a routing function.

    # --- Learning Point: Correct Conditional Routing ---
    # 1. The graph's official entry point is our new dummy node.
    # 2. The conditional edge STARTS from this entry_point node.
    # 3. It uses our 'route_to_context_or_planner' function to inspect the
    #    state and decide which real first step to take.
    workflow.set_entry_point("entry_point")
    workflow.add_conditional_edges(
        "entry_point",
        route_to_context_or_planner,
        {
            "summarize_context": "summarize_context",
            "planner": "planner",
        },
    )

    # Define the rest of the graph flow
    workflow.add_edge("summarize_context", "planner")
    workflow.add_edge("planner", "searcher")
    workflow.add_edge("searcher", "summarizer")
    workflow.add_edge("summarizer", "synthesizer")
    workflow.set_finish_point("synthesizer")

    # Compile the graph
    app = workflow.compile()
    return app


if __name__ == "__main__":
    init_db()
    app = build_graph()
    graph_diagram = app.get_graph().draw_mermaid_png()
    with open("graph_diagram.png", "wb") as f:
        f.write(graph_diagram)

    # --- Interactive Loop ---
    while True:
        print("\n" + "="*50)
        user_id = input("Enter your User ID (e.g., 'user_123') or type 'exit' to quit: ")
        if user_id.lower() == 'exit':
            break

        topic = input("Enter the research topic: ")
        
        # --- Learning Point: Handling Boolean Input ---
        # The input() function returns a string. We need to convert the
        # user's "yes" or "no" into a True or False boolean value for our graph.
        follow_up_str = input("Is this a follow-up question? (yes/no): ")
        follow_up = follow_up_str.lower() in ['y', 'yes', 'true']

        inputs = {"topic": topic, "user_id": user_id, "follow_up": follow_up}

        print("\n--- Generating Research Brief... ---")
        final_state = app.invoke(inputs)
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

            # Save the successful brief to the database for future context
            save_brief(user_id, brief)