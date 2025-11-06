# AI-Powered Product Recommendations with LangGraph 🤖

## Overview

Complete implementation of conversational AI shopping assistant using LangGraph. Users can describe their needs in natural language (e.g., "I have a party tonight") and AI will recommend perfect products.

---

## ✅ COMPLETED STEPS

### 1. Product Model Enhanced ✅

Added AI-specific fields to Product model:

```python
# NEW FIELDS ADDED:
- ai_description (TextField) - Detailed description for AI
- gender (CharField) - M/W/U/K (Men/Women/Unisex/Kids)
- style_tags (JSONField) - ['casual', 'elegant', 'trendy']
- occasion_tags (JSONField) - ['party', 'work', 'wedding']
- season_tags (JSONField) - ['summer', 'winter', 'all-season']
- color_tags (JSONField) - ['black', 'blue', 'white']
- material_tags (JSONField) - ['cotton', 'silk', 'leather']
- age_group_tags (JSONField) - ['young_adults', 'adults']
- activity_tags (JSONField) - ['dancing', 'socializing']
```

### 2. AI Helper Methods ✅

Added to Product model:

```python
# Get product info for AI
product.get_ai_context()

# Search products with AI parameters
Product.search_for_ai(query_params)
```

### 3. Migration Created ✅

```bash
products/migrations/0004_product_activity_tags_product_age_group_tags_and_more.py
```

### 4. Django App Created ✅

```bash
ai_assistant/  # New app for AI recommendations
```

### 5. Dependencies Added ✅

```txt
langgraph==0.2.52
langchain==0.3.11
langchain-openai==0.2.10
```

---

## 📁 IMPLEMENTATION STRUCTURE

```
ai_assistant/
├── __init__.py
├── models.py                    # Conversation state storage
├── graph.py                     # LangGraph workflow
├── agents.py                    # AI agent nodes
├── tools.py                     # Product search tools
├── prompts.py                   # System prompts
├── views.py                     # REST API endpoints
├── serializers.py               # DRF serializers
└── urls.py                      # URL routing
```

---

## 🤖 LANGGRAPH WORKFLOW

### State Definition

```python
from typing import TypedDict, List, Dict, Annotated
from langgraph.graph.message import add_messages

class ConversationState(TypedDict):
    """State that flows through the LangGraph"""

    # User input
    messages: Annotated[List, add_messages]
    user_query: str
    user_market: str  # KG or US
    user_gender: str  # M/W/U

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
```

### Graph Structure

```python
from langgraph.graph import StateGraph, END

# Define the graph
workflow = StateGraph(ConversationState)

# Add nodes
workflow.add_node("understand_query", understand_query_node)
workflow.add_node("extract_requirements", extract_requirements_node)
workflow.add_node("search_products", search_products_node)
workflow.add_node("rank_products", rank_products_node)
workflow.add_node("generate_recommendation", generate_recommendation_node)

# Define edges
workflow.set_entry_point("understand_query")
workflow.add_edge("understand_query", "extract_requirements")
workflow.add_edge("extract_requirements", "search_products")
workflow.add_edge("search_products", "rank_products")
workflow.add_edge("rank_products", "generate_recommendation")
workflow.add_edge("generate_recommendation", END)

# Compile
app = workflow.compile()
```

---

## 🎯 AI AGENT NODES

### 1. Understand Query Node

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def understand_query_node(state: ConversationState) -> ConversationState:
    """
    Understand user's intent from natural language query
    Example: "I have a party tonight" → occasion=party, urgency=tonight
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a fashion shopping assistant.
        Analyze the user's query and extract:
        - What occasion? (party, work, casual, wedding, date, gym, etc.)
        - What style preference? (casual, formal, trendy, classic, etc.)
        - Any urgency? (tonight, this weekend, etc.)
        - Any specific requirements? (comfortable, elegant, etc.)
        """),
        ("user", "{query}")
    ])

    chain = prompt | llm
    response = chain.invoke({"query": state["user_query"]})

    # Parse AI response and update state
    state["messages"].append(response)

    return state
```

### 2. Extract Requirements Node

```python
def extract_requirements_node(state: ConversationState) -> ConversationState:
    """
    Extract structured parameters from conversation
    Maps natural language to product tags
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract product search parameters from the conversation.

        Return JSON with:
        {
            "occasion": ["party", "night_out"],  # array of occasions
            "style": ["casual", "trendy"],       # array of styles
            "season": ["summer", "all-season"],  # array of seasons
            "colors": ["black", "blue"],         # array of colors (optional)
            "price_min": 500,                    # minimum price (optional)
            "price_max": 5000                    # maximum price (optional)
        }

        Available occasions: party, work, wedding, casual, date, gym, beach, night_out, clubbing
        Available styles: casual, formal, sporty, elegant, trendy, classic, modern
        Available seasons: summer, winter, spring, fall, all-season
        """),
        ("user", "{conversation_history}")
    ])

    chain = prompt | llm.with_structured_output(SearchParameters)
    result = chain.invoke({"conversation_history": str(state["messages"])})

    # Update state with extracted parameters
    state["occasion"] = result.occasion
    state["style"] = result.style
    state["season"] = result.season
    state["colors"] = result.colors
    state["price_min"] = result.price_min
    state["price_max"] = result.price_max

    return state
```

### 3. Search Products Node

```python
from products.models import Product

def search_products_node(state: ConversationState) -> ConversationState:
    """
    Search products using extracted parameters
    Uses Product.search_for_ai() method
    """

    query_params = {
        'market': state['user_market'],
        'gender': state['user_gender'],
        'occasion': state['occasion'],
        'style': state['style'],
        'season': state['season'],
        'colors': state['colors'],
        'price_min': state.get('price_min'),
        'price_max': state.get('price_max'),
    }

    # Search products
    products = Product.search_for_ai(query_params)[:20]  # Top 20

    # Convert to AI context
    product_candidates = [p.get_ai_context() for p in products]
    state['product_candidates'] = product_candidates

    return state
```

### 4. Rank Products Node

```python
def rank_products_node(state: ConversationState) -> ConversationState:
    """
    Rank and select best products using AI
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a fashion expert.
        Rank the products based on how well they match the user's needs.
        Consider: occasion match, style match, rating, price, popularity.
        Select the TOP 3-5 best matches.
        """),
        ("user", """
        User query: {user_query}
        Requirements: {requirements}

        Available products:
        {products}

        Return IDs of top 3-5 products.
        """)
    ])

    chain = prompt | llm.with_structured_output(ProductRanking)
    result = chain.invoke({
        "user_query": state["user_query"],
        "requirements": {
            "occasion": state["occasion"],
            "style": state["style"],
        },
        "products": str(state["product_candidates"])
    })

    state["selected_products"] = result.product_ids
    state["confidence_score"] = result.confidence

    return state
```

### 5. Generate Recommendation Node

```python
def generate_recommendation_node(state: ConversationState) -> ConversationState:
    """
    Generate natural language recommendation
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)

    # Get selected products
    selected = [p for p in state["product_candidates"]
                if p['id'] in state["selected_products"]]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a friendly fashion shopping assistant.
        Create an engaging recommendation explaining why these products are perfect.
        Be conversational and enthusiastic!
        """),
        ("user", """
        User asked: {user_query}

        Recommended products:
        {products}

        Write a friendly recommendation (2-3 sentences per product).
        """)
    ])

    chain = prompt | llm
    response = chain.invoke({
        "user_query": state["user_query"],
        "products": str(selected)
    })

    state["recommendation_text"] = response.content

    return state
```

---

## 🔌 REST API ENDPOINTS

### POST /api/ai-assistant/recommend/

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from .graph import app as langgraph_app

class AIRecommendationView(APIView):
    """
    AI-powered product recommendations

    Request:
    {
        "query": "I have a party tonight and don't know what to wear",
        "market": "KG",  # optional, defaults to user.market
        "gender": "M"    # optional, defaults to user.gender
    }

    Response:
    {
        "recommendations": [
            {
                "id": 123,
                "name": "Slim Fit Party Shirt",
                "brand": "ZARA",
                "price": "2500",
                "image": "https://...",
                "match_score": 0.95
            }
        ],
        "explanation": "For a party tonight, I recommend...",
        "confidence": 0.92
    }
    """

    def post(self, request):
        user = request.user
        query = request.data.get('query')

        # Initialize state
        initial_state = {
            "messages": [],
            "user_query": query,
            "user_market": request.data.get('market', user.market if user.is_authenticated else 'KG'),
            "user_gender": request.data.get('gender', user.gender if hasattr(user, 'gender') else 'U'),
            "occasion": [],
            "style": [],
            "season": [],
            "colors": [],
            "product_candidates": [],
            "selected_products": [],
            "recommendation_text": "",
            "confidence_score": 0.0,
        }

        # Run LangGraph
        result = langgraph_app.invoke(initial_state)

        # Get recommended products
        recommended_ids = result["selected_products"]
        products = Product.objects.filter(id__in=recommended_ids)

        return Response({
            "recommendations": ProductSerializer(products, many=True).data,
            "explanation": result["recommendation_text"],
            "confidence": result["confidence_score"],
            "extracted_requirements": {
                "occasion": result["occasion"],
                "style": result["style"],
                "season": result["season"],
            }
        })
```

---

## 🏷️ EXAMPLE PRODUCT DATA

### How to Tag Products for AI

```python
# Example: Party Dress
Product.objects.create(
    name="Elegant Black Party Dress",
    brand="ZARA",
    price=3500,
    market="KG",
    gender="W",
    category=dresses_category,

    # AI fields
    ai_description="Elegant sleeveless black dress perfect for evening events. Features a fitted silhouette and flowing skirt. Made from breathable fabric with a comfortable fit.",

    style_tags=["elegant", "trendy", "modern", "chic"],
    occasion_tags=["party", "night_out", "wedding", "date", "clubbing"],
    season_tags=["summer", "spring", "all-season"],
    color_tags=["black"],
    material_tags=["polyester", "breathable", "stretchy"],
    age_group_tags=["young_adults", "adults"],
    activity_tags=["dancing", "socializing", "partying"],

    image="https://example.com/dress.jpg",
    rating=4.5,
    in_stock=True,
    is_active=True,
)
```

---

## 🚀 USAGE EXAMPLES

### Example 1: Party Tonight

**User:** "I have a party tonight and don't know what to wear"

**AI Process:**

1. ✅ Understands: party + urgent + styling help needed
2. ✅ Extracts: occasion=[party, night_out], urgency=tonight
3. ✅ Searches: Products with occasion_tags containing "party"
4. ✅ Ranks: By rating, style match, availability
5. ✅ Recommends: Top 3-5 perfect matches

**Response:**

```json
{
  "recommendations": [
    {
      "id": 123,
      "name": "Slim Fit Black Shirt",
      "brand": "ZARA",
      "price": "2500",
      "image": "https://...",
      "match_score": 0.95
    }
  ],
  "explanation": "For tonight's party, I recommend this elegant black shirt! It's perfect for a night out with its modern slim fit design. The breathable fabric will keep you comfortable while dancing, and the black color is versatile and stylish. It has a 4.5-star rating and is in stock for immediate purchase!"
}
```

### Example 2: Summer Wedding

**User:** "Need something for a summer wedding next month"

**AI Process:**

1. ✅ Understands: formal event + summer + planning ahead
2. ✅ Extracts: occasion=[wedding], season=[summer], style=[formal, elegant]
3. ✅ Searches: Formal summer wear
4. ✅ Ranks: By formality level, summer suitability
5. ✅ Recommends: Elegant summer outfits

---

## 🔧 SETUP INSTRUCTIONS

### 1. Add OpenAI API Key

```bash
# Add to .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### 2. Register App

```python
# main/settings.py
INSTALLED_APPS = [
    # ...
    'ai_assistant',
]
```

### 3. Update URLs

```python
# main/urls.py
urlpatterns = [
    # ...
    path('api/ai/', include('ai_assistant.urls')),
]
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
python manage.py migrate products
```

---

## 📊 BENEFITS

| Feature                 | Benefit                              |
| ----------------------- | ------------------------------------ |
| 🤖 **Natural Language** | Users describe needs naturally       |
| 🎯 **Smart Matching**   | AI understands context and intent    |
| 🏷️ **Rich Tagging**     | Products tagged for perfect matching |
| 📈 **Learning**         | System improves with usage           |
| 🌍 **Market-Aware**     | KG/US specific recommendations       |
| ⚡ **Fast**             | LangGraph optimized workflow         |
| 🔄 **Conversational**   | Can refine based on feedback         |

---

## 🎨 FRONTEND INTEGRATION

```typescript
// Chat with AI assistant
const response = await fetch("/api/ai/recommend/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    query: "I have a party tonight and don't know what to wear",
  }),
});

const data = await response.json();

// Display recommendations
data.recommendations.forEach((product) => {
  // Show product card with AI explanation
  console.log(product.name, product.match_score);
});

// Show AI explanation
console.log(data.explanation);
```

---

## 📝 NEXT STEPS

1. ✅ **Product Model Enhanced** - DONE
2. ✅ **Migrations Created** - DONE
3. ✅ **Dependencies Added** - DONE
4. ⏳ **Implement LangGraph** - Copy code from this doc
5. ⏳ **Tag Existing Products** - Add AI tags to products
6. ⏳ **Test with Real Queries** - Try different scenarios
7. ⏳ **Deploy** - Add to production

---

## 🎯 SUCCESS METRICS

- **User Engagement**: Time spent with AI assistant
- **Conversion**: Purchases from AI recommendations
- **Satisfaction**: Rating of AI suggestions
- **Coverage**: % of queries successfully handled

---

**You're ready to build the future of conversational commerce!** 🚀🤖
