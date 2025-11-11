'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '@/contexts/AppContext';
import { Send, User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { queryApi, type SourceReference } from '@/lib/api';

export default function CenterChat() {
  const { messages, addMessage, updateMessage, sessionId, darkMode } = useApp();
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Math.random().toString(36).substr(2, 9),
      role: 'user' as const,
      content: input,
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInput('');
    setIsLoading(true);

    // Create assistant message with empty content for streaming
    const assistantId = Math.random().toString(36).substr(2, 9);
    const assistantMessage = {
      id: assistantId,
      role: 'assistant' as const,
      content: '',
      timestamp: new Date(),
      sources: [] as SourceReference[],
    };

    addMessage(assistantMessage);
    setCurrentStreamingId(assistantId);

    try {
      // Use WebSocket for streaming response
      let currentContent = '';

      wsRef.current = queryApi.createStreamConnection(
        userMessage.content,
        sessionId,
        // On chunk received
        (chunk: string) => {
          currentContent += chunk;
          updateMessage(assistantId, {
            content: currentContent,
          });
        },
        // On complete with sources
        (sources: SourceReference[]) => {
          updateMessage(assistantId, {
            sources,
            citations: sources.map((s) => s.filename),
          });
          setIsLoading(false);
          setCurrentStreamingId(null);
        },
        // On error
        (error: string) => {
          updateMessage(assistantId, {
            content: `Error: ${error}`,
          });
          setIsLoading(false);
          setCurrentStreamingId(null);
        }
      );
    } catch (error) {
      console.error('Failed to send query:', error);
      updateMessage(assistantId, {
        content: `Error: Failed to process your query. Please make sure the backend is running.`,
      });
      setIsLoading(false);
      setCurrentStreamingId(null);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-white dark:bg-gray-800">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Chat Assistant
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Ask questions about internship opportunities
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Welcome to Internship Matcher
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
              Upload internship documents and start asking questions. I'll help you find the best matches!
            </p>
            <div className="mt-6 space-y-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">Try asking:</p>
              <div className="space-y-1">
                {[
                  'What are the requirements for data science internships?',
                  'Find remote software engineering opportunities',
                  'Show me internships requiring Python skills',
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion)}
                    className="block w-full px-4 py-2 text-sm text-left text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`flex max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                >
                  <div
                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.role === 'user'
                        ? 'bg-blue-600 ml-3'
                        : 'bg-gray-200 dark:bg-gray-700 mr-3'
                      }`}
                  >
                    {message.role === 'user' ? (
                      <User className="w-5 h-5 text-white" />
                    ) : (
                      <Bot className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                    )}
                  </div>

                  <div
                    className={`rounded-lg p-4 ${message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                      }`}
                  >
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      {message.role === 'user' ? (
                        <p className="m-0">{message.content}</p>
                      ) : (
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                      )}
                    </div>

                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                        <p className="text-xs font-semibold mb-1 opacity-75">Sources:</p>
                        <div className="flex flex-wrap gap-1">
                          {message.citations.map((citation, idx) => (
                            <span
                              key={idx}
                              className="text-xs px-2 py-1 bg-white/10 rounded hover:bg-white/20 cursor-pointer transition-colors"
                              title={message.sources?.[idx]?.content || citation}
                            >
                              📄 {citation}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="flex">
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mr-3">
                    <Bot className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                  </div>
                  <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-4">
                    <div className="flex items-center space-x-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Searching knowledge base...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about internships..."
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
