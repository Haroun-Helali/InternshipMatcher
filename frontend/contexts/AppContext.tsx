'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

// Types
export interface Document {
  id: string;
  title: string;
  status: 'processing' | 'embedded' | 'error';
  created_at: string;
  file_name: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: string[];
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
}

interface AppContextType {
  // Documents
  documents: Document[];
  addDocument: (doc: Document) => void;
  removeDocument: (id: string) => void;
  
  // Messages
  messages: Message[];
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  
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

  const addDocument = (doc: Document) => {
    setDocuments((prev) => [...prev, doc]);
  };

  const removeDocument = (id: string) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== id));
  };

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const clearMessages = () => {
    setMessages([]);
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
        messages,
        addMessage,
        clearMessages,
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
