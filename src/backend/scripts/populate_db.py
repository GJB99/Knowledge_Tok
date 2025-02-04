import asyncio
import arxiv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Content, Base
from database import DATABASE_URL, ARTICLES_DATABASE_URL

# arXiv's main categories
ARXIV_CATEGORIES = {
    'cs': ['AI', 'CL', 'CV', 'LG', 'NE', 'RO'],  # Computer Science
    'physics': ['comp-ph'],  # Computational Physics
    'q-bio': ['BM', 'NC'],  # Quantitative Biology
    'math': ['NA', 'ST'],   # Mathematics
    'astro-ph': ['GA'],     # Astrophysics
    'cond-mat': ['stat-mech', 'dis-nn']  # Condensed Matter
}

async def fetch_arxiv_papers(max_results=1000):
    client = arxiv.Client()
    date_filter = datetime.now() - timedelta(days=30)
    
    papers = []
    for main_cat, subcats in ARXIV_CATEGORIES.items():
        for subcat in subcats:
            category = f"{main_cat}.{subcat}" if main_cat != subcat else main_cat
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            results = list(client.results(search))
            for paper in results:
                if paper.published > date_filter:
                    papers.append({
                        'title': paper.title,
                        'abstract': paper.summary,
                        'url': paper.pdf_url,
                        'external_id': paper.entry_id,
                        'source': 'arxiv',
                        'published_date': paper.published,
                        'paper_metadata': {
                            'authors': [author.name for author in paper.authors],
                            'categories': [cat for cat in paper.categories],
                            'paper_id': paper.entry_id.split('/')[-1],
                            'published_date': paper.published.isoformat()
                        }
                    })
            print(f"Fetched {len(results)} papers from {category}")
    
    return papers

async def store_papers(papers):
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        for paper in papers:
            existing = await session.execute(
                select(Content).where(Content.external_id == paper['external_id'])
            )
            if not existing.scalar_one_or_none():
                content = Content(
                    title=paper['title'],
                    abstract=paper['abstract'],
                    url=paper['url'],
                    external_id=paper['external_id'],
                    source=paper['source'],
                    published_date=paper['published_date'],
                    paper_metadata=paper['paper_metadata']
                )
                session.add(content)
        
        await session.commit()

async def main():
    papers = await fetch_arxiv_papers()
    print(f"Fetched {len(papers)} papers")
    await store_papers(papers)
    print("Database population complete!")

if __name__ == "__main__":
    asyncio.run(main()) 