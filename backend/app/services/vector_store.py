"""Vector store service using ChromaDB for document storage and retrieval."""
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.core.config import get_settings
from backend.app.core.exceptions import VectorStoreError
from backend.app.core.logging import get_logger
from backend.app.models.document import DocumentChunk

logger = get_logger(__name__)


class VectorStore:
    """Vector store for managing document embeddings in ChromaDB.
    
    Implements Single Responsibility Principle - only manages vector storage.
    """
    
    def __init__(self):
        """Initialize vector store with ChromaDB client."""
        self.settings = get_settings()
        
        # Ensure persist directory exists
        persist_dir = Path(self.settings.chroma_persist_directory)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.settings.chroma_collection_name,
                metadata={"description": "Internship documents and chunks"}
            )
            
            logger.info(
                f"Initialized ChromaDB collection '{self.settings.chroma_collection_name}' "
                f"with {self.collection.count()} documents"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            raise VectorStoreError(
                message="Failed to initialize vector store",
                details={"error": str(e)}
            )
    
    def add_documents(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        document_id: str
    ) -> None:
        """Add document chunks with embeddings to vector store.
        
        Args:
            chunks: List of document chunks
            embeddings: List of embedding vectors (one per chunk)
            document_id: Unique document identifier
            
        Raises:
            VectorStoreError: If adding documents fails
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                message="Chunks and embeddings must have same length",
                details={
                    "chunks_count": len(chunks),
                    "embeddings_count": len(embeddings)
                }
            )
        
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        try:
            # Prepare data for ChromaDB
            ids = [f"{document_id}_{chunk.chunk_index}" for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [
                {
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "filename": chunk.metadata.filename,
                    "file_size": chunk.metadata.file_size,
                    "page_count": chunk.metadata.page_count or 0,
                    "document_type": chunk.metadata.document_type,
                    **chunk.metadata.custom_metadata
                }
                for chunk in chunks
            ]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(
                f"Added {len(chunks)} chunks for document {document_id} to vector store"
            )
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}", exc_info=True)
            raise VectorStoreError(
                message="Failed to add documents to vector store",
                details={"error": str(e), "document_id": document_id}
            )
    
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar documents using embedding similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return (default from settings)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching documents with metadata and scores
            
        Raises:
            VectorStoreError: If search fails
        """
        if top_k is None:
            top_k = self.settings.top_k_results
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            logger.info(f"Found {len(formatted_results)} similar documents")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}", exc_info=True)
            raise VectorStoreError(
                message="Similarity search failed",
                details={"error": str(e)}
            )
    
    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document from vector store.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of chunks deleted
            
        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            # Query for all chunk IDs with this document_id
            results = self.collection.get(
                where={"document_id": document_id},
                include=[]
            )
            
            if not results["ids"]:
                logger.warning(f"No chunks found for document {document_id}")
                return 0
            
            # Delete all chunks
            self.collection.delete(ids=results["ids"])
            
            deleted_count = len(results["ids"])
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}", exc_info=True)
            raise VectorStoreError(
                message="Failed to delete document",
                details={"error": str(e), "document_id": document_id}
            )
    
    def get_document_count(self) -> int:
        """Get total number of chunks in vector store.
        
        Returns:
            Number of chunks
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection.
        
        Warning: This deletes all data!
        
        Raises:
            VectorStoreError: If clearing fails
        """
        try:
            # Delete the collection
            self.client.delete_collection(self.settings.chroma_collection_name)
            
            # Recreate empty collection
            self.collection = self.client.get_or_create_collection(
                name=self.settings.chroma_collection_name,
                metadata={"description": "Internship documents and chunks"}
            )
            
            logger.warning("Cleared all documents from vector store")
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}", exc_info=True)
            raise VectorStoreError(
                message="Failed to clear collection",
                details={"error": str(e)}
            )
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store.
        
        Returns:
            Dictionary with store statistics
        """
        try:
            count = self.collection.count()
            
            # Get unique document IDs
            results = self.collection.get(include=["metadatas"])
            unique_docs = set()
            if results["metadatas"]:
                unique_docs = {m.get("document_id") for m in results["metadatas"]}
            
            return {
                "total_chunks": count,
                "unique_documents": len(unique_docs),
                "collection_name": self.settings.chroma_collection_name,
                "persist_directory": self.settings.chroma_persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "error": str(e)
            }


def get_vector_store() -> VectorStore:
    """Get VectorStore instance.
    
    Factory function following Dependency Inversion Principle.
    """
    return VectorStore()
