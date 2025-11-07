/**
 * API Service Layer for Backend Communication
 * Handles all HTTP requests to the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Types matching backend API models
export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  message: string;
  chunks_count?: number;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  chunks_count: number;
  metadata: Record<string, any>;
}

export interface DocumentStatsResponse {
  total_documents: number;
  total_chunks: number;
  storage_size_mb: number;
}

export interface SourceReference {
  document_id: string;
  filename: string;
  chunk_index: number;
  content: string;
  similarity_score: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  session_id: string;
}

export interface QueryRequest {
  question: string;
  session_id?: string;
  include_sources?: boolean;
  top_k?: number;
}

export interface ErrorResponse {
  detail: string;
}

/**
 * Document Management API
 */
export const documentsApi = {
  /**
   * Upload a PDF document for processing and embedding
   */
  async upload(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to upload document');
    }

    return response.json();
  },

  /**
   * List all indexed documents
   */
  async list(): Promise<DocumentInfo[]> {
    const response = await fetch(`${API_BASE_URL}/documents`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to fetch documents');
    }

    const data = await response.json();
    return data.documents;
  },

  /**
   * Delete a document from the vector store
   */
  async delete(documentId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to delete document');
    }
  },

  /**
   * Get knowledge base statistics
   */
  async getStats(): Promise<DocumentStatsResponse> {
    const response = await fetch(`${API_BASE_URL}/documents/stats`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to fetch stats');
    }

    return response.json();
  },
};

/**
 * Query API
 */
export const queryApi = {
  /**
   * Submit a query to the RAG pipeline (non-streaming)
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to query');
    }

    return response.json();
  },

  /**
   * Create a WebSocket connection for streaming responses
   */
  createStreamConnection(
    question: string,
    sessionId: string | null,
    onChunk: (chunk: string) => void,
    onComplete: (sources: SourceReference[]) => void,
    onError: (error: string) => void
  ): WebSocket {
    const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
    const ws = new WebSocket(`${wsUrl}/query/stream`);

    ws.onopen = () => {
      const request = {
        question,
        session_id: sessionId,
        include_sources: true,
      };
      ws.send(JSON.stringify(request));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'chunk') {
          onChunk(data.content);
        } else if (data.type === 'sources') {
          onComplete(data.sources);
        } else if (data.type === 'error') {
          onError(data.message);
          ws.close();
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError('Connection error occurred');
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };

    return ws;
  },

  /**
   * Get conversation history for a session
   */
  async getHistory(sessionId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/query/history/${sessionId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to fetch history');
    }

    return response.json();
  },

  /**
   * Clear conversation history for a session
   */
  async clearHistory(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/query/history/${sessionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.detail || 'Failed to clear history');
    }
  },
};

/**
 * Health Check API
 */
export const healthApi = {
  /**
   * Check backend health status
   */
  async check(): Promise<any> {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/health`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return response.json();
  },
};
