"""
Command-line interface for testing RAG pipeline.

This script provides a simple CLI to test the RAG query pipeline without
needing the full API server.

Usage:
    python -m backend.app.cli.rag_cli

    or with specific query:
    python -m backend.app.cli.rag_cli --query "What internships are available?"
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.rag_pipeline import create_rag_pipeline
from backend.app.services.document_processor import get_document_processor
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.vector_store import get_vector_store
from backend.app.core.logging import setup_logging


async def process_and_index_documents(upload_dir: str = "./uploads") -> int:
    """
    Process all PDF documents in upload directory and add to vector store.

    Args:
        upload_dir: Directory containing PDF files

    Returns:
        Number of documents indexed
    """
    print(f"\n📁 Processing documents from: {upload_dir}")

    upload_path = Path(upload_dir)
    if not upload_path.exists():
        print(f"❌ Upload directory not found: {upload_dir}")
        return 0

    pdf_files = list(upload_path.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {upload_dir}")
        return 0

    print(f"Found {len(pdf_files)} PDF file(s)")

    # Create services
    doc_processor = get_document_processor()
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()

    total_chunks = 0

    for pdf_file in pdf_files:
        try:
            print(f"\n📄 Processing: {pdf_file.name}")

            # Process document
            processed_doc = doc_processor.process_pdf(pdf_file)
            print(f"  ✓ Extracted {len(processed_doc.chunks)} chunks")

            # Generate embeddings
            print(f"  🔄 Generating embeddings...")
            texts = [chunk.content for chunk in processed_doc.chunks]
            embeddings = await embedding_service.generate_embeddings_batch(
                texts, batch_size=5
            )
            print(f"  ✓ Generated {len(embeddings)} embeddings")

            # Add to vector store
            print(f"  💾 Adding to vector store...")
            vector_store.add_documents(
                processed_doc.chunks, embeddings, processed_doc.document_id
            )
            added_count = len(processed_doc.chunks)
            print(f"  ✓ Added {added_count} chunks to vector store")

            total_chunks += added_count

        except Exception as e:
            print(f"  ❌ Error processing {pdf_file.name}: {e}")
            continue

    print(f"\n✅ Indexing complete! Total chunks indexed: {total_chunks}")
    return total_chunks


async def interactive_query_mode(rag_pipeline):
    """
    Run interactive query mode where user can ask questions.

    Args:
        rag_pipeline: RAGPipeline instance
    """
    print("\n" + "=" * 60)
    print("🤖 Interactive RAG Query Mode")
    print("=" * 60)
    print("\nType your questions about internships (or 'quit' to exit)")
    print("Commands:")
    print("  - Type 'stream' to toggle streaming mode")
    print("  - Type 'clear' to clear conversation history")
    print("  - Type 'quit' or 'exit' to quit")
    print("=" * 60 + "\n")

    session_id = "cli_session"
    streaming_mode = False

    while True:
        try:
            # Get user input
            question = input("\n💬 You: ").strip()

            if not question:
                continue

            # Handle commands
            if question.lower() in ["quit", "exit"]:
                print("\n👋 Goodbye!")
                break

            if question.lower() == "clear":
                rag_pipeline.clear_conversation(session_id)
                print("✓ Conversation history cleared")
                continue

            if question.lower() == "stream":
                streaming_mode = not streaming_mode
                mode = "enabled" if streaming_mode else "disabled"
                print(f"✓ Streaming mode {mode}")
                continue

            # Execute query
            print("\n🤖 Assistant: ", end="", flush=True)

            if streaming_mode:
                # Streaming mode
                async for token in rag_pipeline.query_stream(
                    question=question, session_id=session_id
                ):
                    print(token, end="", flush=True)
                print()  # New line after streaming
            else:
                # Regular mode
                response = await rag_pipeline.query(
                    question=question, session_id=session_id
                )
                print(response.answer)

                # Show sources
                if response.sources:
                    print("\n📚 Sources:")
                    for i, source in enumerate(response.sources, 1):
                        print(
                            f"  [{i}] {source['source_file']} (Page {source['page_number']})"
                        )

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def single_query_mode(rag_pipeline, question: str, streaming: bool = False):
    """
    Execute a single query and exit.

    Args:
        rag_pipeline: RAGPipeline instance
        question: Question to ask
        streaming: Whether to use streaming mode
    """
    print(f"\n💬 Query: {question}\n")
    print("🤖 Assistant: ", end="", flush=True)

    try:
        if streaming:
            # Streaming mode
            async for token in rag_pipeline.query_stream(question=question):
                print(token, end="", flush=True)
            print()  # New line
        else:
            # Regular mode
            response = await rag_pipeline.query(question=question)
            print(response.answer)

            # Show sources
            if response.sources:
                print("\n📚 Sources:")
                for i, source in enumerate(response.sources, 1):
                    print(
                        f"  [{i}] {source['source_file']} (Page {source['page_number']})"
                    )
                    print(f"      Preview: {source['content_preview']}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline CLI - Test internship query system"
    )
    parser.add_argument(
        "--query", "-q", type=str, help="Single query to execute (then exit)"
    )
    parser.add_argument(
        "--stream",
        "-s",
        action="store_true",
        help="Use streaming mode for responses",
    )
    parser.add_argument(
        "--index",
        "-i",
        action="store_true",
        help="Index documents from upload folder before querying",
    )
    parser.add_argument(
        "--upload-dir",
        "-u",
        type=str,
        default="./uploads",
        help="Upload directory for PDF files (default: ./uploads)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    print("\n" + "=" * 60)
    print("🚀 RAG Pipeline CLI")
    print("=" * 60)

    # Index documents if requested
    if args.index:
        indexed_count = await process_and_index_documents(args.upload_dir)
        if indexed_count == 0:
            print("\n❌ No documents indexed. Exiting.")
            return

    # Create RAG pipeline
    print("\n🔧 Initializing RAG pipeline...")
    rag_pipeline = create_rag_pipeline()

    # Check vector store status
    vector_store = rag_pipeline.vector_store
    doc_count = vector_store.get_document_count()
    print(f"✓ Vector store contains {doc_count} document chunks")

    if doc_count == 0:
        print("\n⚠️  Warning: Vector store is empty!")
        print("   Use --index flag to process and index documents first")
        print("   Example: python -m backend.app.cli.rag_cli --index")
        return

    try:
        # Execute query mode
        if args.query:
            # Single query mode
            await single_query_mode(rag_pipeline, args.query, args.stream)
        else:
            # Interactive mode
            await interactive_query_mode(rag_pipeline)

    finally:
        # Cleanup
        await rag_pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
