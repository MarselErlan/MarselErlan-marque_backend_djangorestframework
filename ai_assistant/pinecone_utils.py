"""
Pinecone Vector Database Integration
Auto-syncs products to Pinecone for semantic search
"""
import os
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Initialize Pinecone client (singleton)
_pinecone_client = None
_embedding_model = None


def get_pinecone_client():
    """Get or create Pinecone client"""
    global _pinecone_client
    if _pinecone_client is None:
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        _pinecone_client = Pinecone(api_key=api_key)
    return _pinecone_client


def get_embedding_model():
    """Get or create embedding model (cached)"""
    global _embedding_model
    if _embedding_model is None:
        # Using a multilingual model for KG/US markets
        _embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _embedding_model


def get_pinecone_index():
    """Get Pinecone index (marque)"""
    pc = get_pinecone_client()
    index_name = "marque"
    
    # Check if index exists, if not create it
    existing_indexes = pc.list_indexes()
    if index_name not in [idx['name'] for idx in existing_indexes]:
        logger.info(f"Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=384,  # all-MiniLM-L6-v2 dimension
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
    
    return pc.Index(index_name)


def generate_product_embedding(product_data: Dict) -> List[float]:
    """
    Generate embedding for a product
    
    Args:
        product_data: Dict with product info (from product.get_ai_context())
    
    Returns:
        List[float]: 384-dimensional embedding vector
    """
    model = get_embedding_model()
    
    # Create rich text for embedding
    text_parts = [
        f"Product: {product_data.get('name', '')}",
        f"Brand: {product_data.get('brand', '')}",
        f"Description: {product_data.get('description', '')}",
        f"Category: {product_data.get('category', '')}",
        f"Gender: {product_data.get('gender', '')}",
    ]
    
    # Add tags
    for tag_type in ['style', 'occasions', 'seasons', 'colors', 'materials', 'activities']:
        tags = product_data.get(tag_type, [])
        if tags:
            text_parts.append(f"{tag_type.title()}: {', '.join(tags)}")
    
    text = " | ".join(text_parts)
    
    # Generate embedding
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def sync_product_to_pinecone(product):
    """
    Sync a single product to Pinecone
    
    Args:
        product: Product model instance
    """
    try:
        if not product.is_active:
            # Delete from Pinecone if inactive
            delete_product_from_pinecone(product.id)
            return
        
        index = get_pinecone_index()
        product_data = product.get_ai_context()
        
        # Generate embedding
        embedding = generate_product_embedding(product_data)
        
        # Prepare metadata (Pinecone has size limits, keep it concise)
        metadata = {
            'product_id': product.id,
            'name': product.name[:100],  # Truncate for safety
            'brand': product.brand[:50],
            'market': product.market,
            'gender': product.gender,
            'category': product.category.name[:50],
            'price': float(product.price),
            'rating': float(product.rating),
            'in_stock': product.in_stock,
            # Tags as comma-separated strings
            'style_tags': ','.join(product.style_tags[:10]) if product.style_tags else '',
            'occasion_tags': ','.join(product.occasion_tags[:10]) if product.occasion_tags else '',
            'season_tags': ','.join(product.season_tags[:5]) if product.season_tags else '',
        }
        
        # Upsert to Pinecone
        index.upsert(
            vectors=[{
                'id': f'product_{product.id}',
                'values': embedding,
                'metadata': metadata
            }],
            namespace=product.market  # Separate KG/US/ALL products
        )
        
        logger.info(f"✅ Synced product {product.id} ({product.name}) to Pinecone")
        
    except Exception as e:
        logger.error(f"❌ Error syncing product {product.id} to Pinecone: {str(e)}")
        # Don't raise - we don't want to block product saves


def delete_product_from_pinecone(product_id: int):
    """
    Delete a product from Pinecone
    
    Args:
        product_id: Product ID
    """
    try:
        index = get_pinecone_index()
        
        # Delete from all namespaces (KG, US, ALL)
        for namespace in ['KG', 'US', 'ALL']:
            index.delete(ids=[f'product_{product_id}'], namespace=namespace)
        
        logger.info(f"🗑️ Deleted product {product_id} from Pinecone")
        
    except Exception as e:
        logger.error(f"❌ Error deleting product {product_id} from Pinecone: {str(e)}")


def search_products_by_text(
    query: str,
    market: str = 'KG',
    top_k: int = 20,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """
    Search products using semantic similarity
    
    Args:
        query: Natural language query
        market: KG/US/ALL
        top_k: Number of results
        filters: Metadata filters (e.g., {'gender': 'W', 'in_stock': True})
    
    Returns:
        List of product IDs with scores
    """
    try:
        index = get_pinecone_index()
        model = get_embedding_model()
        
        # Generate query embedding
        query_embedding = model.encode(query, convert_to_numpy=True).tolist()
        
        # Build Pinecone filter
        pinecone_filter = filters or {}
        if market != 'ALL':
            # Search in market-specific namespace
            namespace = market
        else:
            namespace = 'ALL'
        
        # Search
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=pinecone_filter if pinecone_filter else None,
            include_metadata=True
        )
        
        # Extract product IDs and scores
        products = []
        for match in results.matches:
            products.append({
                'product_id': match.metadata.get('product_id'),
                'score': match.score,
                'metadata': match.metadata
            })
        
        logger.info(f"🔍 Found {len(products)} products for query: '{query[:50]}...'")
        return products
        
    except Exception as e:
        logger.error(f"❌ Error searching Pinecone: {str(e)}")
        return []


def bulk_sync_products_to_pinecone(products_queryset, batch_size=100):
    """
    Bulk sync products to Pinecone
    
    Args:
        products_queryset: Django QuerySet of Product objects
        batch_size: Number of products per batch
    """
    index = get_pinecone_index()
    total = products_queryset.count()
    synced = 0
    failed = 0
    
    logger.info(f"Starting bulk sync of {total} products to Pinecone...")
    
    # Process in batches
    batch = []
    for product in products_queryset.iterator():
        try:
            if not product.is_active:
                continue
            
            product_data = product.get_ai_context()
            embedding = generate_product_embedding(product_data)
            
            metadata = {
                'product_id': product.id,
                'name': product.name[:100],
                'brand': product.brand[:50],
                'market': product.market,
                'gender': product.gender,
                'category': product.category.name[:50],
                'price': float(product.price),
                'rating': float(product.rating),
                'in_stock': product.in_stock,
                'style_tags': ','.join(product.style_tags[:10]) if product.style_tags else '',
                'occasion_tags': ','.join(product.occasion_tags[:10]) if product.occasion_tags else '',
                'season_tags': ','.join(product.season_tags[:5]) if product.season_tags else '',
            }
            
            batch.append({
                'id': f'product_{product.id}',
                'values': embedding,
                'metadata': metadata
            })
            
            # Upsert batch when full
            if len(batch) >= batch_size:
                index.upsert(vectors=batch, namespace=product.market)
                synced += len(batch)
                logger.info(f"Progress: {synced}/{total} products synced")
                batch = []
        
        except Exception as e:
            logger.error(f"Error processing product {product.id}: {str(e)}")
            failed += 1
    
    # Upsert remaining
    if batch:
        for product_batch in batch:
            try:
                market = product_batch['metadata']['market']
                index.upsert(vectors=[product_batch], namespace=market)
                synced += 1
            except Exception as e:
                logger.error(f"Error in final batch: {str(e)}")
                failed += 1
    
    logger.info(f"✅ Bulk sync complete: {synced} synced, {failed} failed")
    return synced, failed

