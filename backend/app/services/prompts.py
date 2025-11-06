"""
Prompt templates for RAG query pipeline.

This module contains all prompt templates used for generating responses
using the RAG (Retrieval-Augmented Generation) approach.
"""

from typing import List, Dict, Any


class PromptTemplates:
    """Collection of prompt templates for different RAG scenarios."""

    # System prompt that defines the AI assistant's behavior
    SYSTEM_PROMPT = """You are an expert internship advisor AI assistant. Your role is to help students find and understand internship opportunities based on the information available in the knowledge base.

Guidelines:
1. ONLY answer questions based on the provided context from internship documents
2. ALWAYS cite your sources by referencing the document name and page number
3. If the context doesn't contain relevant information, clearly state that you don't have that information
4. Be specific and detailed when describing internship opportunities
5. Highlight key requirements, qualifications, and application details
6. Use a professional but friendly tone
7. If multiple internships match the query, compare and contrast them

NEVER:
- Make up information not present in the context
- Provide generic advice not grounded in the provided documents
- Ignore the context and rely on general knowledge"""

    # Template for building the user query with context
    QUERY_TEMPLATE = """Context from internship documents:
{context}

Based on the above context, please answer the following question:
{question}

Remember to cite specific documents and page numbers in your answer."""

    # Template for when no relevant context is found
    NO_CONTEXT_TEMPLATE = """I apologize, but I don't have any relevant information in the internship knowledge base to answer your question: "{question}"

This could mean:
1. No internship documents have been uploaded yet
2. The uploaded documents don't contain information about this topic
3. Try rephrasing your question with different keywords

Would you like to ask about something else, or would you like me to help you refine your question?"""

    # Template for follow-up questions with conversation history
    FOLLOWUP_TEMPLATE = """Previous conversation:
{conversation_history}

New context from internship documents:
{context}

Based on the conversation history and new context, please answer:
{question}

Maintain consistency with previous answers while incorporating new information."""

    # Template for citation formatting
    CITATION_TEMPLATE = """[Source: {source_file}, Page {page_number}]"""

    # Template for summarizing multiple internship opportunities
    SUMMARY_TEMPLATE = """Here are the internship opportunities I found based on your query:

Context:
{context}

Please provide a concise summary of these internship opportunities, highlighting:
1. Company names and internship titles
2. Key requirements and qualifications
3. Application deadlines (if mentioned)
4. Notable benefits or unique aspects

Format the summary as a numbered list for easy reading."""

    @staticmethod
    def build_query_prompt(question: str, context: str) -> str:
        """
        Build a complete query prompt with context.

        Args:
            question: User's question
            context: Retrieved context from vector store

        Returns:
            Formatted prompt string
        """
        return PromptTemplates.QUERY_TEMPLATE.format(
            context=context, question=question
        )

    @staticmethod
    def build_no_context_prompt(question: str) -> str:
        """
        Build a prompt for when no relevant context is found.

        Args:
            question: User's question

        Returns:
            Formatted no-context response
        """
        return PromptTemplates.NO_CONTEXT_TEMPLATE.format(question=question)

    @staticmethod
    def build_followup_prompt(
        question: str, context: str, conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Build a prompt for follow-up questions with conversation history.

        Args:
            question: Current question
            context: Retrieved context
            conversation_history: List of previous Q&A pairs

        Returns:
            Formatted follow-up prompt
        """
        # Format conversation history
        history_text = "\n".join(
            [
                f"Q: {turn['question']}\nA: {turn['answer']}"
                for turn in conversation_history
            ]
        )

        return PromptTemplates.FOLLOWUP_TEMPLATE.format(
            conversation_history=history_text, context=context, question=question
        )

    @staticmethod
    def build_summary_prompt(context: str) -> str:
        """
        Build a prompt for summarizing multiple internship opportunities.

        Args:
            context: Retrieved context from multiple documents

        Returns:
            Formatted summary prompt
        """
        return PromptTemplates.SUMMARY_TEMPLATE.format(context=context)

    @staticmethod
    def format_citation(source_file: str, page_number: int) -> str:
        """
        Format a citation reference.

        Args:
            source_file: Name of the source document
            page_number: Page number in the document

        Returns:
            Formatted citation string
        """
        return PromptTemplates.CITATION_TEMPLATE.format(
            source_file=source_file, page_number=page_number
        )

    @staticmethod
    def format_context_from_chunks(chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into a context string with citations.

        Args:
            chunks: List of document chunks with metadata

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            source = chunk.get("metadata", {}).get("source_file", "Unknown")
            page = chunk.get("metadata", {}).get("page_number", "?")

            citation = PromptTemplates.format_citation(source, page)
            context_parts.append(f"[Document {i}] {citation}\n{content}")

        return "\n\n---\n\n".join(context_parts)


# Convenience function to get the default instance
def get_prompt_templates() -> PromptTemplates:
    """
    Get the default PromptTemplates instance.

    Returns:
        PromptTemplates instance
    """
    return PromptTemplates()
