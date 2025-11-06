"""
URL routing for AI assistant
"""
from django.urls import path
from .views import AIRecommendationView, AIHealthCheckView

app_name = 'ai_assistant'

urlpatterns = [
    # Main AI recommendation endpoint
    path('recommend/', AIRecommendationView.as_view(), name='recommend'),
    
    # Health check
    path('health/', AIHealthCheckView.as_view(), name='health'),
]

