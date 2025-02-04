from datetime import datetime
from . import models
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
            
            # Check if article already exists
            query = select(models.Content).where(
                models.Content.external_id == url
            )
            result = await db.execute(query)
            existing_article = result.scalar_one_or_none()
            
            if not existing_article:
                article = models.Content(
                    title=title,
                    abstract=abstract,
                    source='arxiv',
                    external_id=url,
                    url=url,
                    published_date=datetime.fromisoformat(published.replace('Z', '+00:00'))
                )
                db.add(article)
                stored_articles.append(article)
        
        await db.commit()
        return stored_articles
    except Exception as e:
        await db.rollback()
        raise e 