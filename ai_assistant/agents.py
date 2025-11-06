"""
LangGraph agent nodes for AI recommendations
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from typing import List, Optional
from products.models import Product
import os


# Get OpenAI API key from environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)


class SearchParameters(BaseModel):
    """Structured output for search parameters"""
    occasion: List[str] = Field(default_factory=list, description="Occasions like party, work, wedding")
    style: List[str] = Field(default_factory=list, description="Styles like casual, formal, elegant")
    season: List[str] = Field(default_factory=list, description="Seasons like summer, winter")
    colors: List[str] = Field(default_factory=list, description="Colors like black, blue")
    price_min: Optional[float] = Field(default=None, description="Minimum price")
    price_max: Optional[float] = Field(default=None, description="Maximum price")


class ProductRanking(BaseModel):
    """Structured output for product ranking"""
    product_ids: List[int] = Field(description="List of product IDs ranked by relevance")
    confidence: float = Field(description="Confidence score 0-1")
    reasoning: str = Field(description="Why these products were selected")


def understand_query_node(state):
    """
    Node 1: Understand user's natural language query
    
    Example: "I have a party tonight" → party, urgent, styling help
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a fashion shopping assistant helping users find perfect outfits.
        
        Analyze the user's query and understand:
        - What's the occasion? (party, work, wedding, casual, date, gym, etc.)
        - What's the style preference? (casual, formal, elegant, sporty, etc.)
        - Any urgency? (tonight, this weekend, next month)
        - Any specific needs? (comfortable, breathable, warm, etc.)
        
        Respond with a brief acknowledgment showing you understand their needs.
        """),
        ("user", "{query}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"query": state["user_query"]})
    
    # Add to conversation
    state["messages"].append(HumanMessage(content=state["user_query"]))
    state["messages"].append(AIMessage(content=response.content))
    
    return state


def extract_requirements_node(state):
    """
    Node 2: Extract structured parameters from conversation
    
    Maps natural language to product search parameters
    """
    extraction_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,  # Lower temp for structured extraction
        api_key=OPENAI_API_KEY
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract product search parameters from the user's query.
        
        Return JSON with these fields:
        - occasion: array of occasions (party, work, wedding, casual, date, gym, beach, night_out, clubbing)
        - style: array of styles (casual, formal, sporty, elegant, trendy, classic, modern)
        - season: array of seasons (summer, winter, spring, fall, all-season)
        - colors: array of colors (black, white, blue, red, etc.) - optional
        - price_min: minimum price in local currency - optional
        - price_max: maximum price in local currency - optional
        
        If something isn't mentioned, use empty array or null.
        Be generous with tags - include related concepts.
        
        Example:
        "I have a party tonight" → occasion: ["party", "night_out"], style: ["trendy", "elegant"]
        """),
        ("user", "{query}")
    ])
    
    chain = prompt | extraction_llm.with_structured_output(SearchParameters)
    result = chain.invoke({"query": state["user_query"]})
    
    # Update state
    state["occasion"] = result.occasion
    state["style"] = result.style
    state["season"] = result.season if result.season else ["all-season"]
    state["colors"] = result.colors
    state["price_min"] = result.price_min
    state["price_max"] = result.price_max
    
    return state


def search_products_node(state):
    """
    Node 3: Search products using semantic search (Pinecone)
    
    Uses Pinecone for semantic/vector search + fallback to tag-based search
    """
    from ai_assistant.pinecone_utils import search_products_by_text
    
    # Build semantic search query from user input and extracted parameters
    search_parts = [state['user_query']]
    if state['occasion']:
        search_parts.append(f"for {', '.join(state['occasion'])}")
    if state['style']:
        search_parts.append(f"with {', '.join(state['style'])} style")
    if state['season']:
        search_parts.append(f"suitable for {', '.join(state['season'])}")
    
    semantic_query = " ".join(search_parts)
    
    # Try Pinecone semantic search first
    try:
        pinecone_results = search_products_by_text(
            query=semantic_query,
            market=state['user_market'],
            top_k=20,
            filters={
                'in_stock': True,
                # Gender filter: match user's gender or unisex
                'gender': {'$in': [state['user_gender'], 'U']}
            }
        )
        
        # Get Product objects from Pinecone results
        product_ids = [r['product_id'] for r in pinecone_results]
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        
        # Sort by Pinecone relevance score (maintain order)
        products_dict = {p.id: p for p in products}
        products = [products_dict[pid] for pid in product_ids if pid in products_dict]
        
    except Exception as e:
        # Fallback to tag-based search if Pinecone fails
        print(f"⚠️ Pinecone search failed, using tag-based search: {str(e)}")
        
        query_params = {
            'market': state['user_market'],
            'gender': state['user_gender'],
            'occasion': state['occasion'],
            'style': state['style'],
            'season': state['season'],
            'colors': state['colors'],
        }
        
        if state.get('price_min'):
            query_params['price_min'] = state['price_min']
        if state.get('price_max'):
            query_params['price_max'] = state['price_max']
        
        products = Product.search_for_ai(query_params)[:20]
    
    # Convert to AI context
    product_candidates = [p.get_ai_context() for p in products[:20]]
    state['product_candidates'] = product_candidates
    
    return state


def rank_products_node(state):
    """
    Node 4: Rank products and select best matches
    
    AI evaluates each product and selects top 3-5
    """
    if not state['product_candidates']:
        # No products found
        state['selected_products'] = []
        state['confidence_score'] = 0.0
        return state
    
    ranking_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=OPENAI_API_KEY
    )
    
    # Format products for AI
    products_summary = "\n\n".join([
        f"ID: {p['id']}\nName: {p['name']}\nBrand: {p['brand']}\nPrice: {p['price']}\n"
        f"Description: {p['description'][:200]}\n"
        f"Occasions: {', '.join(p['occasions'])}\nStyles: {', '.join(p['style'])}\n"
        f"Rating: {p['rating']}"
        for p in state['product_candidates'][:15]  # Limit to avoid token limits
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a fashion expert selecting the perfect products.
        
        Evaluate products based on:
        1. Occasion match - Does it fit the event?
        2. Style match - Does it match the user's style preference?
        3. Quality indicators - Rating, brand reputation
        4. Value - Price appropriate for occasion
        
        Select the TOP 3-5 best matches.
        If no good matches, select empty list.
        
        Provide:
        - product_ids: List of product IDs (top picks first)
        - confidence: 0-1 score of how good the matches are
        - reasoning: Brief explanation of why these products
        """),
        ("user", """
        User asked: {user_query}
        
        Requirements:
        - Occasions: {occasions}
        - Styles: {styles}
        - Season: {season}
        - Market: {market}
        
        Available products:
        {products}
        
        Select the best 3-5 products.
        """)
    ])
    
    chain = prompt | ranking_llm.with_structured_output(ProductRanking)
    result = chain.invoke({
        "user_query": state["user_query"],
        "occasions": ', '.join(state["occasion"]) or 'any',
        "styles": ', '.join(state["style"]) or 'any',
        "season": ', '.join(state["season"]) or 'all-season',
        "market": state["user_market"],
        "products": products_summary
    })
    
    state["selected_products"] = result.product_ids[:5]  # Max 5 products
    state["confidence_score"] = result.confidence
    
    return state


def generate_recommendation_node(state):
    """
    Node 5: Generate natural language recommendation
    
    Create engaging, conversational product recommendations
    """
    if not state['selected_products']:
        state['recommendation_text'] = (
            "I couldn't find products that perfectly match your needs right now. "
            "Could you provide more details about what you're looking for? "
            "For example, preferred style, colors, or price range?"
        )
        return state
    
    # Get selected products
    selected_products = [
        p for p in state['product_candidates'] 
        if p['id'] in state['selected_products']
    ]
    
    # Format products for recommendation
    products_detail = "\n\n".join([
        f"{i+1}. {p['name']} by {p['brand']}\n"
        f"   Price: {p['price']}\n"
        f"   Description: {p['description'][:150]}\n"
        f"   Perfect for: {', '.join(p['occasions'][:3])}\n"
        f"   Style: {', '.join(p['style'][:3])}\n"
        f"   Rating: {p['rating']}/5"
        for i, p in enumerate(selected_products)
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a friendly and enthusiastic fashion shopping assistant.
        
        Create an engaging recommendation that:
        1. Acknowledges the user's needs
        2. Explains why each product is perfect for them
        3. Highlights key features (style, comfort, occasion-fit)
        4. Shows enthusiasm and confidence
        5. Keeps it conversational (2-3 sentences per product)
        
        Be warm, helpful, and persuasive!
        """),
        ("user", """
        User asked: {user_query}
        
        Recommended products:
        {products}
        
        Write a friendly recommendation.
        """)
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "user_query": state["user_query"],
        "products": products_detail
    })
    
    state["recommendation_text"] = response.content
    
    return state

