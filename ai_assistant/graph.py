"""
LangGraph workflow for AI-powered product recommendations
"""
from typing import TypedDict, List, Dict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ConversationState(TypedDict):
    """State that flows through the LangGraph workflow"""
    
    # User input
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    user_market: str  # KG or US
    user_gender: str  # M/W/U/K
    
    # Extracted requirements
    occasion: List[str]  # ['party', 'night_out']
    style: List[str]  # ['casual', 'trendy']
    season: List[str]  # ['summer']
    colors: List[str]  # ['black', 'blue']
    price_min: float
    price_max: float
    
    # Product candidates
    product_candidates: List[Dict]  # Raw product data
    selected_products: List[int]  # Product IDs
    
    # Recommendation
    recommendation_text: str
    confidence_score: float


def create_recommendation_graph():
    """
    Create the LangGraph workflow for product recommendations
    
    Workflow:
    1. understand_query - Analyze user's natural language query
    2. extract_requirements - Extract structured search parameters
    3. search_products - Find matching products
    4. rank_products - Rank and select best matches
    5. generate_recommendation - Create natural language response
    """
    from .agents import (
        understand_query_node,
        extract_requirements_node,
        search_products_node,
        rank_products_node,
        generate_recommendation_node
    )
    
    # Create graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("understand_query", understand_query_node)
    workflow.add_node("extract_requirements", extract_requirements_node)
    workflow.add_node("search_products", search_products_node)
    workflow.add_node("rank_products", rank_products_node)
    workflow.add_node("generate_recommendation", generate_recommendation_node)
    
    # Define flow
    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "extract_requirements")
    workflow.add_edge("extract_requirements", "search_products")
    workflow.add_edge("search_products", "rank_products")
    workflow.add_edge("rank_products", "generate_recommendation")
    workflow.add_edge("generate_recommendation", END)
    
    # Compile
    return workflow.compile()


# Global compiled graph
recommendation_graph = create_recommendation_graph()

