import asyncio
import arxiv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, JSON, update
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import directly from the modules
from models import Content, Base
from database import DATABASE_URL, ARTICLES_DATABASE_URL

async def enrich_content():
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(Content).where(Content.paper_metadata.is_(None))
        )
        contents = result.scalars().all()
        
        print(f"Found {len(contents)} papers that need metadata enrichment")
        
        if not contents:
            print("No papers need enrichment. Exiting...")
            return
            
        proceed = input("Do you want to proceed with enrichment? (y/n): ")
        if proceed.lower() != 'y':
            print("Enrichment cancelled")
            return

        client = arxiv.Client()
        enriched_count = 0
        
        for content in contents:
            if content.url and 'arxiv.org' in content.url:
                arxiv_id = content.url.split('/')[-1]
                try:
                    search = arxiv.Search(id_list=[arxiv_id])
                    results = list(client.results(search))
                    if results:
                        paper = results[0]
                        
                        # Start a new transaction for each paper
                        async with session.begin_nested():
                            await session.execute(
                                update(Content)
                                .where(Content.id == content.id)
                                .values(paper_metadata={
                                    'authors': [author.name for author in paper.authors],
                                    'categories': [cat for cat in paper.categories],
                                    'paper_id': arxiv_id,
                                    'published_date': paper.published.isoformat()
                                })
                            )
                            await session.commit()
                        
                        enriched_count += 1
                        print(f"Enriched paper ({enriched_count}/{len(contents)}): {content.title}")
                except Exception as e:
                    print(f"Error enriching {content.title}: {e}")
                    continue

        print(f"Database enrichment complete! Enriched {enriched_count} papers")

if __name__ == "__main__":
    asyncio.run(enrich_content()) 