'use client';

import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useApp } from '@/contexts/AppContext';
import { useToast } from '@/contexts/ToastContext';
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { documentsApi } from '@/lib/api';

export default function LeftSidebar() {
  const { documents, addDocument, removeDocument, updateDocument, darkMode, mobileLeftOpen, closeMobileLeft } = useApp();
  const { toast } = useToast();
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);

  // Load existing documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const docs = await documentsApi.list();
      docs.forEach((doc) => {
        addDocument({
          id: doc.document_id,
          title: doc.filename,
          status: 'embedded',
          created_at: new Date().toISOString(),
          file_name: doc.filename,
          chunks_count: doc.chunks_count,
        });
      });
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const pollUntilReady = async (documentId: string, filename: string) => {
    // Backend processes embeddings asynchronously; poll until ready/failed.
    // Cap at ~5min total to avoid running forever on a stalled job.
    const MAX_ATTEMPTS = 150;
    for (let i = 0; i < MAX_ATTEMPTS; i++) {
      try {
        const status = await documentsApi.getStatus(documentId);
        if (status.state === 'ready') {
          updateDocument(documentId, {
            status: 'embedded',
            chunks_count: status.chunks_indexed,
          });
          toast('success', `${filename} indexed (${status.chunks_indexed} chunks)`);
          return;
        }
        if (status.state === 'failed') {
          updateDocument(documentId, { status: 'error' });
          toast('error', `${filename} failed: ${status.error ?? 'unknown error'}`);
          return;
        }
      } catch (err) {
        console.error('Status poll failed:', err);
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    updateDocument(documentId, { status: 'error' });
    toast('error', `${filename} indexing timed out`);
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      setUploadProgress(`Uploading ${file.name} (${fileSizeMB} MB)…`);

      const tempId = Math.random().toString(36).substr(2, 9);
      addDocument({
        id: tempId,
        title: file.name,
        status: 'processing',
        created_at: new Date().toISOString(),
        file_name: file.name,
      });

      try {
        const response = await documentsApi.upload(file);
        // Swap the optimistic id for the real document_id and start polling.
        updateDocument(tempId, {
          id: response.document_id,
          status: 'processing',
        });
        setUploadProgress(null);
        toast('info', `${file.name} uploaded — indexing in background…`);
        // Don't await — let multiple uploads poll in parallel.
        pollUntilReady(response.document_id, file.name);
      } catch (error) {
        updateDocument(tempId, { status: 'error' });
        setUploadProgress(null);
        const msg = error instanceof Error ? error.message : 'Upload failed';
        toast('error', `${file.name}: ${msg}`);
        console.error('Failed to upload document:', error);
      }
    }
  }, [addDocument, updateDocument, toast]); const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'embedded':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const handleDelete = async (doc: any) => {
    try {
      await documentsApi.delete(doc.id);
      removeDocument(doc.id);
      toast('success', `${doc.title} deleted`);
    } catch (error) {
      console.error('Failed to delete document:', error);
      const msg = error instanceof Error ? error.message : 'Failed to delete document';
      toast('error', msg);
    }
  };

  return (
    <>
      {mobileLeftOpen && (
        <div
          onClick={closeMobileLeft}
          className="md:hidden fixed inset-0 z-30 bg-black/40"
          aria-hidden="true"
        />
      )}
      <div
        className={`
          ${mobileLeftOpen ? 'fixed inset-y-0 left-0 z-40 flex w-80' : 'hidden'}
          md:static md:flex md:w-80
          bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex-col
        `}
      >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Documents
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Upload internship PDFs
          </p>
        </div>
        <button
          onClick={closeMobileLeft}
          className="md:hidden p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="Close documents"
        >
          <span className="text-xl leading-none">×</span>
        </button>
      </div>

      {/* Upload Area */}
      <div className="p-4">
        {uploadProgress && (
          <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-600 dark:text-blue-400">{uploadProgress}</p>
          </div>
        )}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500'
            }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400 dark:text-gray-500" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {isDragActive ? (
              'Drop PDFs here...'
            ) : (
              <>
                Drag & drop PDFs or <span className="text-blue-600 dark:text-blue-400">browse</span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">
          Uploaded ({documents.length})
        </h3>

        {documents.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 mx-auto mb-2 text-gray-300 dark:text-gray-600" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No documents yet
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 group hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {doc.title}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                      {getStatusIcon(doc.status)}
                      <span className="capitalize">{doc.status}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(doc)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-opacity"
                    aria-label="Delete document"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </>
  );
}
