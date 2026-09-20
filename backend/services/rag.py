from typing import Any

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Document, Embedding


class RAGService:
    def __init__(self, db_session: AsyncSession, embedding_model: str = "text-embedding-ada-002"):
        self.db = db_session
        self.embedding_model = embedding_model

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Simple character-based chunking."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Fetch embeddings via LiteLLM."""
        response = await litellm.aembedding(
            model=self.embedding_model,
            input=texts
        )
        return [item["embedding"] for item in response["data"]]

    async def ingest_document(self, title: str, content: str) -> Document:
        """Chunk a document, embed it, and store it in pgvector."""
        doc = Document(title=title, content=content)
        self.db.add(doc)
        await self.db.flush()
        
        chunks = self.chunk_text(content)
        embeddings = await self.get_embeddings(chunks)
        
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings, strict=True)):
            embedding_record = Embedding(
                document_id=doc.id,
                chunk_index=idx,
                chunk_content=chunk,
                embedding=emb
            )
            self.db.add(embedding_record)
            
        await self.db.commit()
        return doc

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for relevant chunks using cosine similarity."""
        query_embedding = (await self.get_embeddings([query]))[0]
        
        # Calculate cosine distance (1 - cosine similarity). 
        # pgvector uses `<=>` for cosine distance.
        stmt = (
            select(Embedding, Document)
            .join(Document)
            .order_by(Embedding.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        results = []
        for emb, doc in rows:
            results.append({
                "document_title": doc.title,
                "chunk_content": emb.chunk_content,
                # Cosine distance to similarity: 1 - distance
                "similarity": 1.0 - float(emb.embedding.cosine_distance(query_embedding))
            })
            
        return results
