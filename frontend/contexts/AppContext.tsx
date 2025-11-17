'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

// Types
export interface Document {
  id: string;
  title: string;
  status: 'processing' | 'embedded' | 'error';
  created_at: string;
  file_name: string;
  chunks_count?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: string[];
  sources?: Array<{
    document_id: string;
    filename: string;
    chunk_index: number;
    content: string;
    similarity_score: number;
  }>;
}

export interface Profile {
  skills: string[];
  education: string[];
  experience: string[];
}

export interface Match {
  id: string;
  company: string;
  position: string;
  matchScore: number;
  matchingSkills: string[];
  description: string;
  documentId?: string;
  filename?: string;
  chunkIndex?: number;
}

interface AppContextType {
  // Documents
  documents: Document[];
  addDocument: (doc: Document) => void;
  removeDocument: (id: string) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;

  // Messages
  messages: Message[];
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;

  // Session
  sessionId: string;
  generateNewSession: () => void;

  // Profile
  profile: Profile | null;
  setProfile: (profile: Profile | null) => void;

  // Matches
  matches: Match[];
  setMatches: (matches: Match[]) => void;

  // UI State
  darkMode: boolean;
  toggleDarkMode: () => void;
  rightSidebarOpen: boolean;
  toggleRightSidebar: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [darkMode, setDarkMode] = useState(false);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [sessionId, setSessionId] = useState<string>(() => {
    // Generate initial session ID
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  });

  const addDocument = (doc: Document) => {
    setDocuments((prev) => [...prev, doc]);
  };

  const removeDocument = (id: string) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== id));
  };

  const updateDocument = (id: string, updates: Partial<Document>) => {
    setDocuments((prev) =>
      prev.map((doc) => (doc.id === id ? { ...doc, ...updates } : doc))
    );
  };

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const updateMessage = (id: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
    );
  };

  const clearMessages = () => {
    setMessages([]);
  };

  const generateNewSession = () => {
    setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  };

  const toggleDarkMode = () => {
    setDarkMode((prev) => !prev);
  };

  const toggleRightSidebar = () => {
    setRightSidebarOpen((prev) => !prev);
  };

  return (
    <AppContext.Provider
      value={{
        documents,
        addDocument,
        removeDocument,
        updateDocument,
        messages,
        addMessage,
        updateMessage,
        clearMessages,
        sessionId,
        generateNewSession,
        profile,
        setProfile,
        matches,
        setMatches,
        darkMode,
        toggleDarkMode,
        rightSidebarOpen,
        toggleRightSidebar,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
