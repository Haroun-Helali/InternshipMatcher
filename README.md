# 🎓 Internship RAG Application

An AI-powered internship matching and discovery platform using Retrieval-Augmented Generation (RAG) to help students find relevant internship opportunities through semantic search and natural language interaction.

## 🚀 Features

- **Semantic Search**: Find internships using natural language queries
- **Resume Analysis**: Automatically extract skills and experience from resumes
- **Intelligent Matching**: AI-powered matching between student profiles and internships
- **Document Processing**: Parse and index internship descriptions from PDFs
- **Interactive Chat**: Conversational interface for exploring opportunities

## 🏗️ Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Next.js        │ ◄─────► │  FastAPI        │ ◄─────► │  RAG Engine     │
│  Frontend       │  HTTP   │  Backend        │  Python │  (LangChain)    │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                                  │
                                    ┌─────────────────────────────┼─────────────────┐
                                    │                             │                 │
                              ┌─────▼─────┐             ┌────────▼────────┐  ┌────▼────┐
                              │  Ollama   │             │    ChromaDB     │  │  Docs   │
                              │    LLM    │             │  Vector Store   │  │ Parser  │
                              └───────────┘             └─────────────────┘  └─────────┘
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.10+
- **RAG**: LangChain
- **LLM**: Ollama (llama3.2:latest)
- **Embeddings**: mxbai-embed-large:latest
- **Vector DB**: ChromaDB (local)
- **Document Processing**: PyPDF2, python-docx

### Frontend (Coming in later phases)
- **Framework**: Next.js 14+
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context API

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Ollama** ([Download](https://ollama.ai/download))
- **Git** (for version control)
- **Node.js 18+** (for frontend in later phases)

### Install Ollama Models

After installing Ollama, pull the required models:

```powershell
ollama pull llama3.2:latest
ollama pull mxbai-embed-large:latest
```

Verify Ollama is running:
```powershell
ollama list
```

## 🚀 Quick Start

### 1. Clone the Repository

```powershell
cd C:\Users\Yacin\Desktop\project
```

### 2. Set Up Python Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Python Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env file with your preferred text editor
notepad .env
```

Verify these settings in `.env`:
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_EMBEDDING_MODEL=mxbai-embed-large:latest`
- `OLLAMA_LLM_MODEL=llama3.2:latest`

### 5. Create Required Directories

The application will create these automatically, but you can create them manually:

```powershell
mkdir -p logs, chroma_data, uploads, temp_files
```

### 6. Run the Application

```powershell
# Development mode (with auto-reload)
python -m backend.app.main

# Or using uvicorn directly
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Health Check**: http://localhost:8000/health

## 🧪 Running Tests

```powershell
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_config.py

# Run with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov-report=html
# Open htmlcov/index.html in browser
```

## 📁 Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── core/           # Core configuration, logging, exceptions
│   │   ├── api/            # API endpoints (routers)
│   │   ├── services/       # Business logic services
│   │   ├── models/         # Pydantic models
│   │   ├── utils/          # Utility functions
│   │   └── main.py         # FastAPI application entry point
│   └── __init__.py
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest configuration
├── docs/                   # Documentation
├── uploads/                # Uploaded document storage
├── temp_files/             # Temporary file processing
├── chroma_data/            # ChromaDB persistence
├── logs/                   # Application logs
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Example environment configuration
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Python project configuration
└── README.md               # This file
```

## 🔧 Development

### Code Quality Tools

This project follows SOLID principles and uses modern Python tooling:

```powershell
# Format code with Black
black backend/

# Lint with Ruff
ruff check backend/

# Type check with MyPy
mypy backend/

# Run all quality checks
black backend/ && ruff check backend/ && mypy backend/ && pytest
```

### Adding New Dependencies

```powershell
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

## 📝 Development Phases

This application is being built incrementally following a structured phase approach:

- ✅ **Phase 0**: Project Foundation & Environment Setup (COMPLETE)
- ✅ **Phase 1**: Core RAG Engine - Document Processing (COMPLETE)
- ✅ **Phase 2**: Vector Store Integration (COMPLETE)
- 🔄 **Phase 3**: Basic RAG Query Pipeline (NEXT)
- ⏳ **Phase 4**: FastAPI Backend - Document Management
- ⏳ **Phase 5**: FastAPI Backend - Query Endpoints
- ⏳ **Phase 6**: Resume Processing Module
- ⏳ **Phase 7**: Intelligent Matching Engine
- ⏳ **Phase 8-12**: Next.js Frontend Development
- ⏳ **Phase 13**: Polish, Testing & Deployment

See `rag_dev_prompt.md` for detailed phase descriptions.

## 🐛 Troubleshooting

### Ollama Connection Issues

```powershell
# Check if Ollama is running
ollama list

# Restart Ollama service
# On Windows: Restart Ollama from system tray
```

### Virtual Environment Issues

```powershell
# Deactivate current environment
deactivate

# Remove and recreate
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Import Errors

Make sure you're running commands from the project root and the virtual environment is activated:
```powershell
# Check current directory
pwd
# Should output: C:\Users\Yacin\Desktop\project

# Check if venv is active (you should see (venv) in prompt)
```

### ChromaDB Issues

```powershell
# Clear ChromaDB data
Remove-Item -Recurse -Force chroma_data
```

## 🤝 Contributing

This is currently a learning/development project. Future contribution guidelines will be added.

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Ollama Documentation](https://ollama.ai/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)

## ✨ Next Steps

After Phase 2 completion:

1. **Test embeddings**: Run integration tests to verify Ollama connectivity
2. **Verify vector store**: Check ChromaDB persistence in `./chroma_data`
3. **Review Phase 2 docs**: Read `docs/PHASE_2_COMPLETE.md` for implementation details
4. **Run full test suite**: Execute `pytest` to ensure all 40 tests pass
5. **Ready for Phase 3**: Begin RAG query pipeline implementation

---

**Current Version**: 0.1.0  
**Status**: Phase 2 Complete ✅ (40/40 tests passing)  
**Last Updated**: 2024-01-XX
