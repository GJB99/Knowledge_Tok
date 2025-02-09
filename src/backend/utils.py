from datetime import datetime
from .models import Content
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, JSON, update, func, and_, or_, desc
import xml.etree.ElementTree as ET
import asyncio
import arxiv
import sys
import os
from sentence_transformers import SentenceTransformer
import numpy as np

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import directly from the modules
from .models import Content, Base  # Use relative import
from .database import DATABASE_URL, ARTICLES_DATABASE_URL

# Load a pre-trained model (all-MiniLM-L6-v2 is fast and good for many tasks)
model = SentenceTransformer('all-MiniLM-L6-v2')

async def get_embedding(text: str, db: AsyncSession):
    """
    Gets the embedding for a given text.  Checks the database first,
    and if not found, generates it using SentenceTransformer.
    """
    # Check if the embedding exists
    embedding_check_query = select(Content.embedding).where(
        or_(
            Content.title == text,
            Content.abstract == text
        )
    )
    existing_embedding = await db.execute(embedding_check_query)
    try:
        existing_embedding_result = existing_embedding.scalar_one_or_none()
    except Exception as e: # catch exception
        existing_embedding_result = None

    if existing_embedding_result is not None:
        return existing_embedding_result

    # Generate and return the embedding
    embedding = model.encode(text).tolist()  # Convert numpy array to list
    return embedding

async def similarity_search(query_embedding: list, db: AsyncSession, content_ids_to_exclude=None, limit: int = 100):
    """
    Performs a similarity search using cosine similarity.
    This is a simplified, in-memory implementation.
    """
    # Ensure the query embedding is a numpy array
    query_embedding_np = np.array(query_embedding)

    # Build the base query
    query = select(
        Content.id,
        Content.title,
        Content.abstract,
        Content.source,
        Content.url,
        Content.published_date,
        Content.paper_metadata,
        Content.embedding
    ).where(Content.embedding.is_not(None))

    # Exclude content IDs if provided
    if content_ids_to_exclude:
        query = query.where(Content.id.not_in(content_ids_to_exclude))

    # Execute the query
    result = await db.execute(query)
    all_articles = result.all()

    # Calculate cosine similarity for each article
    similarities = []
    for article in all_articles:
        if article.embedding:
            article_embedding_np = np.array(article.embedding)
            # Calculate cosine similarity
            similarity = np.dot(query_embedding_np, article_embedding_np) / (np.linalg.norm(query_embedding_np) * np.linalg.norm(article_embedding_np))
            similarities.append((article, similarity))

    # Sort by similarity (descending)
    sorted_articles = sorted(similarities, key=lambda x: x[1], reverse=True)

    # Return the top 'limit' articles
    return [article for article, similarity in sorted_articles[:limit]]

async def process_and_store_arxiv_results(xml_data: str, db: AsyncSession):
    try:
        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        stored_articles = []
        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text
            abstract = entry.find('atom:summary', namespace).text
            url = entry.find('atom:id', namespace).text
            published = entry.find('atom:published', namespace).text
            
            # Extract categories and authors
            categories = [cat.get('term') for cat in entry.findall('atom:category', namespace)]
            authors = [author.find('atom:name', namespace).text for author in entry.findall('atom:author', namespace)]
            paper_id = url.split('/')[-1]
            
            # Check if article already exists
            query = select(Content).where(
                Content.external_id == url
            )
            result = await db.execute(query)
            existing_article = result.scalar_one_or_none()
            
            if not existing_article:
                # Get embeddings for title and abstract
                title_embedding = await get_embedding(title, db)
                abstract_embedding = await get_embedding(abstract, db)

                # Combine title and abstract embeddings (simple average)
                combined_embedding = ((np.array(title_embedding) + np.array(abstract_embedding)) / 2).tolist()

                article = Content(
                    title=title,
                    abstract=abstract,
                    source='arxiv',
                    external_id=url,
                    url=url,
                    published_date=datetime.fromisoformat(published.replace('Z', '+00:00')),
                    paper_metadata={
                        'categories': categories,
                        'authors': authors,
                        'paper_id': paper_id,
                        'published_date': published
                    },
                    embedding = combined_embedding
                )
                db.add(article)
                stored_articles.append(article)
        
        await db.commit()
        return stored_articles
    except Exception as e:
        await db.rollback()
        raise e 