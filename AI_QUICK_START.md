# AI Recommendations - Quick Start 🚀

## 5-Minute Setup

### Step 1: Add OpenAI API Key

```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-your-api-key-here" >> .env
```

### Step 2: Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run Migrations

```bash
python manage.py migrate products
```

### Step 4: Update main/urls.py

```python
# main/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ai/', include('ai_assistant.urls')),  # ADD THIS LINE
    # ... other paths
]
```

### Step 5: Test the System

```bash
# Start server
python manage.py runserver

# Check health
curl http://localhost:8000/api/ai/health/

# Test recommendation (in new terminal)
curl -X POST http://localhost:8000/api/ai/recommend/ \
  -H "Content-Type: application/json" \
  -d '{"query": "I have a party tonight"}'
```

---

## Tag Your First Product

```python
python manage.py shell

from products.models import Product, Category

# Get or create category
category = Category.objects.first()

# Create AI-enabled product
product = Product.objects.create(
    name="Elegant Black Party Dress",
    brand="ZARA",
    price=3500,
    market="KG",
    gender="W",
    category=category,

    # AI tags - THE MAGIC! ✨
    ai_description="Elegant sleeveless black dress perfect for evening events",
    style_tags=["elegant", "trendy", "chic"],
    occasion_tags=["party", "night_out", "wedding"],  # <-- KEY!
    season_tags=["summer", "all-season"],
    color_tags=["black"],
    material_tags=["polyester", "breathable"],
    activity_tags=["dancing", "socializing"],

    image="https://example.com/dress.jpg",
    rating=4.5,
    in_stock=True,
    is_active=True,
)

print("✅ Product created! Try: 'I need something for a party'")
```

---

## Test It!

```bash
curl -X POST http://localhost:8000/api/ai/recommend/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a party tonight and dont know what to wear",
    "market": "KG",
    "gender": "W"
  }'
```

**Response:**

```json
{
  "success": true,
  "recommendations": [
    {
      "id": 1,
      "name": "Elegant Black Party Dress",
      "brand": "ZARA",
      "price": "3500.00",
      "image": "https://example.com/dress.jpg",
      "rating": 4.5
    }
  ],
  "explanation": "For tonight's party, I recommend this elegant black dress by ZARA! It's perfect for evening events with its chic design and breathable fabric. You'll look stunning and feel comfortable while dancing. The 4.5-star rating confirms it's a crowd favorite!",
  "confidence": 0.95,
  "extracted_requirements": {
    "occasion": ["party", "night_out"],
    "style": ["elegant", "trendy"],
    "season": ["all-season"]
  }
}
```

---

## Tag Bulk Products

```python
# Bulk update existing products
from products.models import Product

# Update all party-appropriate products
party_products = Product.objects.filter(
    category__name__icontains="dress"
).update(
    occasion_tags=["party", "wedding", "date"]
)

# Update casual products
Product.objects.filter(
    category__name__icontains="shirt"
).update(
    style_tags=["casual", "comfortable"],
    occasion_tags=["casual", "work", "everyday"]
)

print(f"✅ Updated products!")
```

---

## Frontend Integration

```typescript
// React/Next.js
async function getAIRecommendations(query: string) {
  const response = await fetch("http://localhost:8000/api/ai/recommend/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`, // if using auth
    },
    body: JSON.stringify({ query }),
  });

  const data = await response.json();

  return {
    products: data.recommendations,
    explanation: data.explanation,
    confidence: data.confidence,
  };
}

// Usage
const result = await getAIRecommendations("I have a party tonight");
```

---

## Common Queries to Test

```bash
# Party/Event
"I have a party tonight"
"Need something for a wedding next week"
"Going to a formal dinner"

# Casual
"Looking for comfortable everyday wear"
"Need something for weekend shopping"

# Work
"Professional outfit for office meeting"
"Business casual for work"

# Season-specific
"Need warm clothes for winter"
"Light breathable outfit for summer"

# Style-specific
"Want something trendy and modern"
"Classic elegant style"
"Sporty casual look"
```

---

## Troubleshooting

### "missing_api_key" Error

```bash
# Make sure .env has your key
cat .env | grep OPENAI_API_KEY

# Should show: OPENAI_API_KEY=sk-...

# Restart server after adding key
```

### "No products found" Response

```bash
# Check product tags
python manage.py shell
>>> from products.models import Product
>>> Product.objects.filter(occasion_tags__isnull=False).count()

# Should be > 0
# If 0, products need AI tags!
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check installations
pip list | grep langchain
pip list | grep langgraph
```

---

## Next Steps

1. ✅ **Tag More Products** - Add AI tags to all your products
2. ✅ **Test Different Queries** - Try various natural language inputs
3. ✅ **Customize Prompts** - Edit `ai_assistant/agents.py` to tune AI behavior
4. ✅ **Add Authentication** - Change `AllowAny` to `IsAuthenticated` in views
5. ✅ **Monitor Usage** - Track which queries work best
6. ✅ **Collect Feedback** - Ask users if recommendations were helpful

---

## Production Checklist

- [ ] Add `OPENAI_API_KEY` to production `.env`
- [ ] Tag all products with AI attributes
- [ ] Enable authentication (`IsAuthenticated`)
- [ ] Add rate limiting
- [ ] Monitor API costs
- [ ] Add analytics tracking
- [ ] Set up error logging
- [ ] Test with real users

---

**You're ready to provide intelligent shopping assistance!** 🎉🤖

See `AI_RECOMMENDATIONS_IMPLEMENTATION.md` for complete technical documentation.
