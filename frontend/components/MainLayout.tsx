'use client';

import React from 'react';
import { useApp } from '@/contexts/AppContext';
import { Moon, Sun, Menu, X } from 'lucide-react';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { darkMode, toggleDarkMode } = useApp();

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🎓</div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  Internship Matcher
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  AI-Powered Internship Discovery
                </p>
              </div>
            </div>
            
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <Sun className="w-5 h-5 text-yellow-500" />
              ) : (
                <Moon className="w-5 h-5 text-gray-700" />
              )}
            </button>
          </div>
        </header>

        {/* Main Content */}
        {children}
      </div>
    </div>
  );
}
