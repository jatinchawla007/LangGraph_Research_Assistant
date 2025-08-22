# app/graph_state.py

from typing import List, Optional
from typing_extensions import TypedDict
from .schemas import ResearchPlan, SourceSummary


class GraphState(TypedDict):
    """
    Represents the state of our research assistant.

    Attributes:
        topic: The initial research topic provided by the user.
        research_plan: The structured plan for conducting the research.
        search_results: A list of search results from the search tool.
        source_summaries: A list of summaries for each researched source.
        final_brief: The compiled final research brief.
    """
    # Inputs
    topic: str
    user_id: str
    follow_up: bool

    topic: str
    research_plan: Optional[ResearchPlan] = None
    search_results: Optional[List[dict]] = None
    source_summaries: Optional[List[SourceSummary]] = None
    final_brief: Optional[str] = None