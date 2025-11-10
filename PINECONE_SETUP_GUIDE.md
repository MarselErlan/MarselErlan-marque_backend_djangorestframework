# 🚀 Pinecone Setup Guide

## Quick Setup (3 Steps)

### Step 1: Add Pinecone Credentials to `.env`

```bash
# Add these lines to your .env file
PINECONE_API_KEY=key
PINECONE_HOST=host
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

New packages:

- `pinecone-client==5.0.1`
- `sentence-transformers==3.3.1`

### Step 3: Sync Products to Pinecone

```bash
python manage.py sync_products_to_pinecone
```

This will:

- Create embeddings for all products
- Upload them to Pinecone
- Enable semantic search

---

## 🎉 That's It!

Your AI recommendations now use **semantic search** powered by Pinecone!

### What Changed?

1. **Products auto-sync:** When you save a product in Django admin, it automatically syncs to Pinecone
2. **Smarter search:** AI finds products by meaning, not just tags
3. **Better recommendations:** Users get more relevant product suggestions

### Test It

```bash
curl -X POST http://localhost:8000/api/ai/recommend/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a party tonight and dont know what to wear"
  }'
```

---

## 📚 Full Documentation

See `PINECONE_INTEGRATION.md` for complete technical details.

---

## 🔧 Management Commands

### Bulk Sync All Products

```bash
python manage.py sync_products_to_pinecone
```

### Sync Specific Market

```bash
python manage.py sync_products_to_pinecone --market US
```

### Force Sync (Including Inactive)

```bash
python manage.py sync_products_to_pinecone --force
```

---

## ✅ Verify Setup

```python
python manage.py shell
```

```python
from ai_assistant.pinecone_utils import get_pinecone_client

pc = get_pinecone_client()
print("✅ Pinecone connected successfully!")
print(pc.list_indexes())
```

---

**Questions?** Check `PINECONE_INTEGRATION.md` for troubleshooting.
