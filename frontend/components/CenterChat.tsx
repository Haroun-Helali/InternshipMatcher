'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '@/contexts/AppContext';
import { Send, User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { queryApi, type SourceReference } from '@/lib/api';

export default function CenterChat() {
  const { messages, addMessage, updateMessage, sessionId, darkMode, setMatches } = useApp();
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

  const extractMatchesFromAnswer = (answer: string) => {
    try {
      // First try fenced JSON block
      const codeBlockRegex = /```json\s*([\s\S]*?)```/i;
      let jsonText: string | null = null;
      const fenced = answer.match(codeBlockRegex);
      if (fenced) {
        jsonText = fenced[1];
      } else {
        // Fallback: try to locate a raw JSON object containing "matches"
        const startIdx = answer.lastIndexOf('{');
        const matchesKeyIdx = answer.toLowerCase().lastIndexOf('"matches"');
        if (matchesKeyIdx !== -1) {
          // Walk backward to the preceding '{'
          let i = matchesKeyIdx;
          while (i >= 0 && answer[i] !== '{') i--;
          if (i >= 0) {
            // Balance braces to find the end
            let depth = 0;
            let end = -1;
            for (let j = i; j < answer.length; j++) {
              const ch = answer[j];
              if (ch === '{') depth++;
              else if (ch === '}') {
                depth--;
                if (depth === 0) {
                  end = j;
                  break;
                }
              }
            }
            if (end !== -1) {
              jsonText = answer.slice(i, end + 1);
            }
          }
        }
      }

      if (!jsonText) return null;

      const data = JSON.parse(jsonText);
      if (!data || !Array.isArray(data.matches)) return null;
      return data.matches
        .filter((m: any) => m && (m.title || m.company))
        .map((m: any, idx: number) => ({
          id: `${m.document_id || 'doc'}-${idx}`,
          company: m.title || 'Opportunity',
          position: m.company || 'Internship',
          matchScore: Math.max(0, Math.min(100, Math.round(Number(m.score) || 0))),
          matchingSkills: Array.isArray(m.requirements) ? m.requirements.map((s: any) => String(s)).slice(0, 10) : [],
          description: `${(m.requirements || []).join(', ')}`.slice(0, 240),
          documentId: m.document_id,
          filename: m.source_file,
        }));
    } catch (e) {
      console.error('Failed to parse matches JSON from answer:', e);
      return null;
    }
  };

  const stripMatchesJson = (answer: string) => {
    try {
      // Remove fenced JSON block if present
      const fencedRegex = /```json[\s\S]*?```/i;
      if (fencedRegex.test(answer)) {
        return answer.replace(fencedRegex, '').trim();
      }
      // Remove raw JSON object containing "matches" if present
      const lower = answer.toLowerCase();
      const matchesKeyIdx = lower.lastIndexOf('"matches"');
      if (matchesKeyIdx !== -1) {
        let i = matchesKeyIdx;
        while (i >= 0 && answer[i] !== '{') i--;
        if (i >= 0) {
          let depth = 0;
          let end = -1;
          for (let j = i; j < answer.length; j++) {
            const ch = answer[j];
            if (ch === '{') depth++;
            else if (ch === '}') {
              depth--;
              if (depth === 0) { end = j; break; }
            }
          }
          if (end !== -1) {
            return (answer.slice(0, i) + answer.slice(end + 1)).trim();
          }
        }
      }
      return answer;
    } catch {
      return answer;
    }
  };

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
          // Prefer structured matches from the assistant answer if present
          const structuredMatches = extractMatchesFromAnswer(currentContent);
          const displayContent = stripMatchesJson(currentContent);
          updateMessage(assistantId, {
            content: displayContent,
            sources,
            citations: sources.map((s) => s.filename),
          });
          if (structuredMatches && structuredMatches.length > 0) {
            setMatches(structuredMatches);
          } else {
            // Fallback: map sources to matches
            try {
              const mappedMatches = sources.map((s, idx) => ({
                id: `${s.document_id}-${s.chunk_index}-${idx}`,
                company: s.content?.slice(0, 60) || s.filename || 'Unknown Source',
                position: s.filename || `Chunk ${typeof s.chunk_index === 'number' ? s.chunk_index + 1 : 1}`,
                matchScore: Math.max(0, Math.min(100, Math.round((s.similarity_score ?? 0) * 100))),
                matchingSkills: [],
                description: (s.content || '').slice(0, 240) + ((s.content || '').length > 240 ? '…' : ''),
                documentId: s.document_id,
                filename: s.filename,
                chunkIndex: s.chunk_index,
              }));
              setMatches(mappedMatches);
            } catch (e) {
              console.error('Failed to map sources to matches:', e);
            }
          }
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
