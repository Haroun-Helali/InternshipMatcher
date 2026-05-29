'use client';

import React from 'react';
import { useApp } from '@/contexts/AppContext';
import { Moon, Sun, Menu, Briefcase } from 'lucide-react';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { darkMode, toggleDarkMode, toggleMobileLeft, toggleRightSidebar } = useApp();

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="px-4 md:px-6 py-4 flex items-center justify-between gap-2">
            <div className="flex items-center space-x-3 min-w-0">
              <button
                onClick={toggleMobileLeft}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                aria-label="Open documents"
              >
                <Menu className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              </button>
              <div className="text-2xl">🎓</div>
              <div className="min-w-0">
                <h1 className="text-base md:text-xl font-bold text-gray-900 dark:text-white truncate">
                  Internship Matcher
                </h1>
                <p className="hidden md:block text-sm text-gray-500 dark:text-gray-400">
                  AI-Powered Internship Discovery
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={toggleRightSidebar}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                aria-label="Open matches"
              >
                <Briefcase className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              </button>
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
          </div>
        </header>

        {children}
      </div>
    </div>
  );
}
