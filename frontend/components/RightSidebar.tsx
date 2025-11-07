'use client';

import React, { useState } from 'react';
import { useApp } from '@/contexts/AppContext';
import { Briefcase, Star, TrendingUp, MapPin, Calendar, X, ChevronRight } from 'lucide-react';

export default function RightSidebar() {
  const { matches, rightSidebarOpen, toggleRightSidebar, darkMode, setMatches } = useApp();
  const [selectedMatch, setSelectedMatch] = useState<string | null>(null);

  if (!rightSidebarOpen) {
    return (
      <button
        onClick={toggleRightSidebar}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 border-l border-y border-gray-200 dark:border-gray-700 p-2 rounded-l-lg shadow-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        aria-label="Open sidebar"
      >
        <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400 rotate-180" />
      </button>
    );
  }

  return (
    <div className="w-96 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Match Results
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Top internship matches
          </p>
        </div>
        <button
          onClick={toggleRightSidebar}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Matches List */}
      <div className="flex-1 overflow-y-auto p-4">
        {matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Briefcase className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
              No matches yet
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Upload your resume to find matching internships
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {matches.map((match) => (
              <div
                key={match.id}
                className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer border border-transparent hover:border-blue-200 dark:hover:border-blue-800"
                onClick={() => setSelectedMatch(selectedMatch === match.id ? null : match.id)}
              >
                {/* Company & Position */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {match.company}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {match.position}
                    </p>
                  </div>
                  
                  {/* Match Score */}
                  <div className="ml-3">
                    <div className="flex items-center space-x-1">
                      <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                      <span className="font-bold text-gray-900 dark:text-white">
                        {match.matchScore}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Match Progress Bar */}
                <div className="mb-3">
                  <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        match.matchScore >= 80
                          ? 'bg-green-500'
                          : match.matchScore >= 60
                          ? 'bg-yellow-500'
                          : 'bg-blue-500'
                      }`}
                      style={{ width: `${match.matchScore}%` }}
                    />
                  </div>
                </div>

                {/* Matching Skills */}
                <div className="flex flex-wrap gap-1 mb-2">
                  {match.matchingSkills.slice(0, 3).map((skill, idx) => (
                    <span
                      key={idx}
                      className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded"
                    >
                      {skill}
                    </span>
                  ))}
                  {match.matchingSkills.length > 3 && (
                    <span className="text-xs px-2 py-1 text-gray-500 dark:text-gray-400">
                      +{match.matchingSkills.length - 3} more
                    </span>
                  )}
                </div>

                {/* Expanded Details */}
                {selectedMatch === match.id && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600 space-y-2">
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {match.description}
                    </p>
                    
                    <div className="mt-3">
                      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">
                        All Matching Skills:
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {match.matchingSkills.map((skill, idx) => (
                          <span
                            key={idx}
                            className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    <button className="mt-3 w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
                      View Full Details
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Demo Data Button */}
      {matches.length === 0 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {
              // Add demo matches for demonstration
              const demoMatches = [
                {
                  id: '1',
                  company: 'Tech Corp',
                  position: 'Software Engineering Intern',
                  matchScore: 92,
                  matchingSkills: ['Python', 'React', 'TypeScript', 'Git'],
                  description: 'Join our team to work on cutting-edge web applications.',
                },
                {
                  id: '2',
                  company: 'Data Insights',
                  position: 'Data Science Intern',
                  matchScore: 85,
                  matchingSkills: ['Python', 'Machine Learning', 'SQL'],
                  description: 'Help us analyze data and build predictive models.',
                },
                {
                  id: '3',
                  company: 'Cloud Systems',
                  position: 'DevOps Intern',
                  matchScore: 78,
                  matchingSkills: ['Docker', 'AWS', 'Python'],
                  description: 'Work with our infrastructure and deployment team.',
                },
              ];
              
              setMatches(demoMatches);
            }}
            className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Load Demo Matches
          </button>
        </div>
      )}
    </div>
  );
}
