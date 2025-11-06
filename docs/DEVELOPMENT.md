# Development Guide

## Overview

This guide covers the development workflow, coding standards, and best practices for the Internship RAG Application.

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each module has one clear purpose
- `config.py` - Only handles configuration
- `logging.py` - Only handles logging setup
- `exceptions.py` - Only defines custom exceptions

### Open/Closed Principle (OCP)
- Base exception class `RAGApplicationError` can be extended
- New exception types can be added without modifying base class
- Configuration is extensible through environment variables

### Liskov Substitution Principle (LSP)
- All custom exceptions inherit from base and can be used interchangeably
- Service interfaces will be designed for substitutability

### Interface Segregation Principle (ISP)
- Small, focused interfaces rather than large monolithic ones
- Services will implement only the methods they need

### Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions (e.g., `get_settings()`)
- Dependency injection used throughout (FastAPI's dependency system)
- Easy to mock and test

## Project Structure Explained

```
backend/app/
├── core/               # Core functionality - config, logging, exceptions
│   ├── config.py      # Environment configuration with Pydantic
│   ├── logging.py     # Structured logging setup
│   └── exceptions.py  # Custom exception hierarchy
├── api/               # API layer - FastAPI routers
│   ├── documents.py   # Document upload/management endpoints
│   ├── query.py       # Query/chat endpoints
│   ├── resume.py      # Resume parsing endpoints
│   └── match.py       # Matching endpoints
├── services/          # Business logic layer
│   ├── document_processor.py    # Document parsing & chunking
│   ├── embedding_service.py     # Embedding generation
│   ├── vector_store.py          # ChromaDB operations
│   ├── rag_pipeline.py          # RAG orchestration
│   ├── resume_parser.py         # Resume extraction
│   └── matching_engine.py       # Matching algorithm
├── models/            # Pydantic models for data validation
│   ├── document.py    # Document-related schemas
│   ├── query.py       # Query-related schemas
│   ├── resume.py      # Resume/profile schemas
│   └── match.py       # Match result schemas
├── utils/             # Utility functions
│   ├── file_utils.py  # File handling utilities
│   └── text_utils.py  # Text processing utilities
└── main.py            # FastAPI application entry point
```

## Development Workflow

### Starting Development

1. **Activate virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Run application in development mode**:
   ```powershell
   python -m backend.app.main
   ```
   Or with uvicorn directly:
   ```powershell
   uvicorn backend.app.main:app --reload
   ```

3. **Access API documentation**:
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc

### Adding New Features

Follow the incremental phase approach:

1. **Plan the feature** - Understand requirements clearly
2. **Write tests first** (TDD approach when possible)
3. **Implement core logic** - Keep functions small (<50 lines)
4. **Add error handling** - Use custom exceptions
5. **Add API endpoint** (if needed)
6. **Document the code** - Docstrings for all public functions
7. **Test integration** - Run full test suite
8. **Update README** - Document new functionality

### Code Quality Checklist

Before committing code:

- [ ] Code is formatted with Black
- [ ] No linting errors from Ruff
- [ ] Type hints added for all functions
- [ ] Docstrings added (Google style)
- [ ] Tests written and passing
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] No hardcoded values (use config)

## Testing Strategy

### Unit Tests
- Test individual functions in isolation
- Mock external dependencies (Ollama, ChromaDB)
- Fast execution (<1 second per test)
- Location: `tests/unit/`

Example:
```python
def test_chunk_text():
    """Test text chunking with specific parameters."""
    text = "Sample text..."
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 0
    assert all(len(chunk) <= 100 for chunk in chunks)
```

### Integration Tests
- Test multiple components working together
- Use real ChromaDB instance (test collection)
- Mock only external APIs (Ollama)
- Location: `tests/integration/`

Example:
```python
async def test_document_upload_pipeline(client):
    """Test full document upload and embedding flow."""
    response = client.post("/api/v1/documents/upload", files={"file": pdf_file})
    assert response.status_code == 200
    # Verify document in ChromaDB
```

### Running Tests

```powershell
# All tests
pytest

# Specific test file
pytest tests/unit/test_config.py

# With coverage
pytest --cov=backend --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

## Error Handling Best Practices

### Use Custom Exceptions

```python
from backend.app.core.exceptions import DocumentProcessingError

def process_pdf(file_path: str) -> str:
    """Process PDF and extract text."""
    try:
        text = extract_text_from_pdf(file_path)
        return text
    except Exception as e:
        raise DocumentProcessingError(
            message=f"Failed to process PDF: {file_path}",
            details={"error": str(e), "file": file_path}
        )
```

### Log Errors Appropriately

```python
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

def risky_operation():
    try:
        # ... operation
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

## API Design Principles

### RESTful Endpoints

- Use appropriate HTTP methods: GET, POST, PUT, DELETE
- Use plural nouns for resources: `/documents`, `/queries`
- Version your API: `/api/v1/`
- Return appropriate status codes

### Request/Response Models

Always use Pydantic models for validation:

```python
from pydantic import BaseModel, Field

class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class DocumentResponse(BaseModel):
    """Response model for document."""
    id: str
    title: str
    status: str
    created_at: datetime
```

### Error Responses

Consistent error response format:

```python
{
    "detail": "Error message",
    "status_code": 400,
    "details": {
        "field": "Additional context"
    }
}
```

## Logging Guidelines

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical messages for very serious errors

### What to Log

```python
# Service start/stop
logger.info("Starting document processing service")

# Important operations
logger.info(f"Processing document: {doc_id}")

# Warnings
logger.warning(f"Large file uploaded: {file_size}MB")

# Errors (with stack trace)
logger.error(f"Failed to embed document: {doc_id}", exc_info=True)

# Performance metrics
logger.info(f"Document processed in {elapsed:.2f}s")
```

### What NOT to Log

- Sensitive information (passwords, tokens, PII)
- Large data dumps
- Inside tight loops (use sampling)

## Configuration Management

### Environment Variables

All configuration should come from environment variables or `.env` file:

```python
from backend.app.core.config import get_settings

settings = get_settings()
ollama_url = settings.ollama_base_url
```

### Never hardcode:
- API URLs
- Model names
- File paths
- Timeouts
- Limits

## Git Workflow

### Commit Messages

Follow conventional commits format:

```
feat: add document chunking service
fix: handle empty PDF files
docs: update API documentation
test: add tests for embedding service
refactor: improve error handling in vector store
```

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch (future)
- Feature branches for new phases

## Performance Considerations

### Async Operations

Use `async/await` for I/O-bound operations:

```python
async def generate_embedding(text: str) -> List[float]:
    """Generate embedding asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ollama_url}/api/embeddings",
            json={"model": model_name, "prompt": text}
        )
    return response.json()["embedding"]
```

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_embedding(text: str) -> List[float]:
    """Get cached embedding for text."""
    return generate_embedding(text)
```

### Batch Processing

Process documents in batches:

```python
def embed_documents_batch(docs: List[Document], batch_size: int = 10):
    """Embed documents in batches for efficiency."""
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        embeddings = generate_embeddings_batch(batch)
        yield embeddings
```

## Security Considerations

### File Upload Security

- Validate file types (check magic bytes, not just extension)
- Limit file sizes
- Sanitize filenames
- Store uploads outside web root
- Scan for malware (future consideration)

### API Security

- Rate limiting (implemented via middleware)
- Input validation (Pydantic models)
- CORS configuration (restrict origins in production)
- No sensitive data in logs or responses

## Documentation Standards

### Docstring Format (Google Style)

```python
def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """Split text into overlapping chunks.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of overlapping characters between chunks
        
    Returns:
        List of text chunks with specified overlap
        
    Raises:
        ValueError: If chunk_size <= overlap
        
    Example:
        >>> chunks = chunk_text("Long text...", chunk_size=100, overlap=20)
        >>> len(chunks)
        5
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    # Implementation...
```

### README Updates

When adding new features, update:
- Feature list
- API endpoints
- Configuration options
- Examples

## Troubleshooting Common Issues

### Import Errors

If you see import errors:
1. Ensure virtual environment is activated
2. Check you're running from project root
3. Verify `backend` is in Python path

### ChromaDB Issues

If ChromaDB fails to initialize:
1. Check `chroma_data` directory permissions
2. Delete and recreate: `Remove-Item -Recurse chroma_data`
3. Verify ChromaDB version compatibility

### Ollama Connection Failures

1. Verify Ollama is running: `ollama list`
2. Check `OLLAMA_BASE_URL` in `.env`
3. Test connection: `curl http://localhost:11434/api/tags`

## Phase-by-Phase Development Notes

### Current Phase: Phase 0 ✅
- Project structure established
- Core configuration implemented
- Logging system set up
- Exception hierarchy defined
- Testing framework configured

### Next Phase: Phase 1
Focus: Document Processing Foundation
- Implement `document_processor.py`
- PDF text extraction
- Text chunking with LangChain
- Metadata extraction
- Unit tests for all functions

## Resources

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [LangChain Documentation](https://python.langchain.com/)
- [Clean Code Principles](https://github.com/zedr/clean-code-python)

---

**Remember**: Code quality over quantity. Take time to do it right the first time.
