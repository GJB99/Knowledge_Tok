import asyncio
import sys
import os
from sqlalchemy import text

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import articles_engine

async def add_metadata_column():
    async with articles_engine.begin() as conn:
        # Add the paper_metadata column if it doesn't exist
        await conn.execute(
            text("""
            ALTER TABLE content 
            ADD COLUMN paper_metadata JSON;
            """)
        )
        print("Added paper_metadata column to content table")

if __name__ == "__main__":
    asyncio.run(add_metadata_column()) 