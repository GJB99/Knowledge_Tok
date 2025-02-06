from datetime import datetime
from .models import Content
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import xml.etree.ElementTree as ET


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
                    }
                )
                db.add(article)
                stored_articles.append(article)
        
        await db.commit()
        return stored_articles
    except Exception as e:
        await db.rollback()
        raise e 