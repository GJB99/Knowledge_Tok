import asyncio
import arxiv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, JSON
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import directly from the modules
from models import Content, Base
from database import DATABASE_URL, ARTICLES_DATABASE_URL

async def enrich_content():
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all existing content
        result = await session.execute(select(Content))
        contents = result.scalars().all()
        
        client = arxiv.Client()
        
        for content in contents:
            # Extract arxiv ID from URL
            if content.url and 'arxiv.org' in content.url:
                arxiv_id = content.url.split('/')[-1]
                try:
                    # Use synchronous search instead of async
                    search = arxiv.Search(id_list=[arxiv_id])
                    results = list(client.results(search))
                    if results:
                        paper = results[0]
                        
                        # Update paper_metadata instead of metadata
                        content.paper_metadata = {
                            'authors': [author.name for author in paper.authors],
                            'categories': [cat for cat in paper.categories],
                            'paper_id': arxiv_id,
                            'published_date': paper.published.isoformat()
                        }
                        
                        print(f"Enriched paper: {content.title}")
                except Exception as e:
                    print(f"Error enriching {content.title}: {e}")
                    continue
        
        await session.commit()
        print("Database enrichment complete!")

if __name__ == "__main__":
    asyncio.run(enrich_content()) 