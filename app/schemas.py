from pydantic import BaseModel, Field
from typing import List

# Pydantic models are used for structured data validation.
# They ensure that the data moving through our application, especially
# from LLM outputs, conforms to a predefined shape.

class ResearchPlan(BaseModel):
    """
    This schema defines the plan the AI will follow to conduct its research.
    """
    topic: str = Field(..., description="The main topic of the research brief.")
    research_questions: List[str] = Field(..., description="A list of specific questions to answer about the topic.")
    search_queries: List[str] = Field(..., description="A list of search engine queries to find relevant information.")

class SourceSummary(BaseModel):
    """
    This schema holds the summary and key details of a single information source.
    """
    url: str = Field(..., description="The URL of the information source.")
    title: str = Field(..., description="The title of the source.")
    key_points: List[str] = Field(..., description="A list of bullet points summarizing the key information from the source.")
    relevance_to_topic: str = Field(..., description="A brief explanation of how this source is relevant to the main topic.")
    relevance_score: float = Field(..., description="A score representing the relevance of this source to the main topic between 0 and 1.")

class FinalBrief(BaseModel):
    """
    This is the final, user-facing research brief. It compiles all the research into a single, structured output.
    """
    topic: str = Field(..., description="The main topic of the research brief.")
    introduction: str = Field(..., description="A brief introduction to the topic.")
    synthesis: str = Field(..., description="A synthesized summary combining information from all sources to answer the research questions.")
    references: List[SourceSummary] = Field(..., description="A list of the summarized sources used to compile the brief.")
    potential_follow_ups: List[str] = Field(..., description="Suggestions for follow-up research questions.")

class BriefRequest(BaseModel):
    """
    This schema defines the structure of a request for a research brief.
    """
    user_id: str = Field(..., description="The ID of the user requesting the brief.")
    topic: str = Field(..., description="The main topic of the research brief.")
    follow_up: bool = False
    search_depth: str = Field(..., description="The depth of the search to perform (e.g., 'basic', 'deep').")