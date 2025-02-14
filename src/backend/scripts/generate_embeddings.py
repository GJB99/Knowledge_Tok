import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
import sys
import os
import numpy as np

# No sys.path modification needed!

# Use RELATIVE imports.
from ..models import Content, Base
from ..database import ARTICLES_DATABASE_URL
from ..utils import get_embedding


async def generate_embeddings():
    engine = create_async_engine(ARTICLES_DATABASE_URL)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all content items that don't have an embedding
        result = await session.execute(
            select(Content).where(Content.embedding.is_(None))
        )
        contents = result.scalars().all()

        print(f"Found {len(contents)} papers without embeddings")

        if not contents:
            print("No papers need embedding generation. Exiting...")
            return

        for content in contents:
            # Store the title *before* any potential exceptions
            content_title = content.title
            try:
                # Combine title and abstract embeddings (simple average)
                title_embedding = await get_embedding(content.title, session)
                abstract_embedding = await get_embedding(content.abstract, session)
                if title_embedding is None or abstract_embedding is None:
                    print(f"Skipping {content_title} due to missing embedding (or duplicate title/abstract).")
                    continue

                combined_embedding = ((np.array(title_embedding) + np.array(abstract_embedding)) / 2).tolist()

                # Update the content item with the combined embedding
                await session.execute(
                    update(Content)
                    .where(Content.id == content.id)
                    .values(embedding=combined_embedding)
                )
                await session.commit()  # Commit after each update
                print(f"Generated embedding for: {content_title}")

            except Exception as e:
                # Use the stored title
                print(f"Error generating embedding for {content_title}: {e}")
                await session.rollback()  # Rollback if error
                continue

        print("Embedding generation complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(generate_embeddings()) 