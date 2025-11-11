"""
REST API views for AI-powered product recommendations
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse
from products.models import Product
from .graph import get_recommendation_graph
import logging

logger = logging.getLogger(__name__)


class AIRecommendationRequestSerializer(serializers.Serializer):
    """Request payload for AI recommendations."""

    query = serializers.CharField()
    market = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)


class RecommendationProductSerializer(serializers.Serializer):
    """Product summary returned by AI recommendations."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    brand = serializers.CharField(required=False, allow_null=True)
    price = serializers.CharField()
    image = serializers.CharField(required=False, allow_null=True)
    rating = serializers.FloatField(required=False, allow_null=True)
    category = serializers.CharField()
    subcategory = serializers.CharField(required=False, allow_null=True)
    in_stock = serializers.BooleanField()
    slug = serializers.CharField()
    discount = serializers.FloatField(required=False, allow_null=True)


class ExtractedRequirementsSerializer(serializers.Serializer):
    """Structured attributes extracted from the natural language prompt."""

    occasion = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    style = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    season = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    colors = serializers.ListField(child=serializers.CharField(), allow_empty=True, required=False)


class AIRecommendationResponseSerializer(serializers.Serializer):
    """Response payload for AI recommendations."""

    success = serializers.BooleanField()
    recommendations = RecommendationProductSerializer(many=True)
    explanation = serializers.CharField()
    confidence = serializers.FloatField()
    extracted_requirements = ExtractedRequirementsSerializer()


class AIHealthCheckResponseSerializer(serializers.Serializer):
    """Health check response payload."""

    status = serializers.CharField()
    openai_configured = serializers.BooleanField()
    products_total = serializers.IntegerField()
    products_with_ai_tags = serializers.IntegerField()
    coverage = serializers.CharField()
    langgraph_loaded = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True)


class AIRecommendationView(APIView):
    """
    AI-powered product recommendations using LangGraph
    
    POST /api/ai/recommend/
    
    Request:
    {
        "query": "I have a party tonight and don't know what to wear",
        "market": "KG",  # optional, defaults to user.market or 'KG'
        "gender": "M"    # optional, defaults to user.gender or 'U'
    }
    
    Response:
    {
        "success": true,
        "recommendations": [
            {
                "id": 123,
                "name": "Slim Fit Party Shirt",
                "brand": "ZARA",
                "price": "2500.00",
                "image": "https://...",
                "rating": 4.5,
                "category": "Shirts",
                "in_stock": true
            }
        ],
        "explanation": "For tonight's party, I recommend...",
        "confidence": 0.92,
        "extracted_requirements": {
            "occasion": ["party", "night_out"],
            "style": ["trendy", "elegant"],
            "season": ["all-season"]
        }
    }
    """
    
    permission_classes = [AllowAny]  # Change to [IsAuthenticated] in production
    
    @extend_schema(
        summary="Generate AI-powered product recommendations",
        tags=["ai"],
        request=AIRecommendationRequestSerializer,
        responses={
            200: AIRecommendationResponseSerializer,
            400: OpenApiResponse(description="Query is required."),
            500: OpenApiResponse(description="Failed to generate recommendations."),
        },
    )
    def post(self, request):
        try:
            # Get request data
            query = request.data.get('query', '').strip()
            
            if not query:
                return Response({
                    "success": False,
                    "error": "Query is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user context
            user = request.user
            
            # Determine market and gender
            if user.is_authenticated:
                user_market = request.data.get('market', user.market)
                user_gender = request.data.get('gender', getattr(user, 'gender', 'U'))
            else:
                user_market = request.data.get('market', 'KG')
                user_gender = request.data.get('gender', 'U')
            
            # Initialize state
            initial_state = {
                "messages": [],
                "user_query": query,
                "user_market": user_market,
                "user_gender": user_gender,
                "occasion": [],
                "style": [],
                "season": [],
                "colors": [],
                "price_min": None,
                "price_max": None,
                "product_candidates": [],
                "selected_products": [],
                "recommendation_text": "",
                "confidence_score": 0.0,
            }
            
            logger.info(f"AI Recommendation request: {query}, market={user_market}, gender={user_gender}")
            
            # Run LangGraph workflow (lazy-loaded)
            result = get_recommendation_graph().invoke(initial_state)
            
            # Get recommended products from database
            recommended_ids = result["selected_products"]
            products = Product.objects.filter(id__in=recommended_ids, is_active=True, in_stock=True)
            
            # Maintain order from AI ranking
            products_dict = {p.id: p for p in products}
            ordered_products = [products_dict[pid] for pid in recommended_ids if pid in products_dict]
            
            # Format products for response
            recommendations = [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "price": str(p.price),
                    "image": p.image,
                    "rating": float(p.rating),
                    "category": p.category.name,
                    "subcategory": p.subcategory.name if p.subcategory else None,
                    "in_stock": p.in_stock,
                    "slug": p.slug,
                    "discount": p.discount,
                }
                for p in ordered_products
            ]
            
            logger.info(f"AI Recommendation success: {len(recommendations)} products, confidence={result['confidence_score']}")
            
            return Response({
                "success": True,
                "recommendations": recommendations,
                "explanation": result["recommendation_text"],
                "confidence": result["confidence_score"],
                "extracted_requirements": {
                    "occasion": result["occasion"],
                    "style": result["style"],
                    "season": result["season"],
                    "colors": result.get("colors", []),
                }
            })
            
        except Exception as e:
            logger.error(f"AI Recommendation error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": "Failed to generate recommendations. Please try again.",
                "detail": str(e) if request.user.is_staff else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIHealthCheckView(APIView):
    """
    Check if AI assistant is configured and working
    
    GET /api/ai/health/
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Check AI assistant health",
        tags=["ai"],
        responses={200: AIHealthCheckResponseSerializer},
    )
    def get(self, request):
        import os
        from langchain_openai import ChatOpenAI
        
        # Check OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY', '')
        has_api_key = bool(api_key and len(api_key) > 10)
        
        # Check product count
        products_with_ai_tags = Product.objects.filter(
            is_active=True,
            in_stock=True
        ).exclude(
            occasion_tags=[]
        ).count()
        
        total_products = Product.objects.filter(is_active=True, in_stock=True).count()
        
        health_status = {
            "status": "healthy" if has_api_key else "missing_api_key",
            "openai_configured": has_api_key,
            "products_total": total_products,
            "products_with_ai_tags": products_with_ai_tags,
            "coverage": f"{(products_with_ai_tags/total_products*100):.1f}%" if total_products > 0 else "0%",
            "langgraph_loaded": True,
        }
        
        if not has_api_key:
            health_status["message"] = "OpenAI API key not configured. Add OPENAI_API_KEY to .env file."
        elif products_with_ai_tags == 0:
            health_status["message"] = "No products have AI tags. Add occasion_tags, style_tags, etc. to products."
        else:
            health_status["message"] = f"AI Assistant is ready! {products_with_ai_tags} products available."
        
        return Response(health_status)
