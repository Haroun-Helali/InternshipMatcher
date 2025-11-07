# Internship Matcher - Frontend

This is the Next.js frontend for the Internship Matcher RAG application.

## Features

- **Three-Panel Layout**: Documents sidebar, chat interface, and match results panel
- **Document Upload**: Drag-and-drop interface for uploading internship PDFs
- **Chat Interface**: Conversational AI assistant for querying internships
- **Match Results**: Display of top internship matches with scoring
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Optimized for desktop and mobile devices

## Technology Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **State Management**: React Context API
- **UI Components**: Custom components with lucide-react icons
- **Markdown Rendering**: react-markdown for AI responses
- **File Upload**: react-dropzone for drag-and-drop

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running on http://localhost:8000

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The application will be available at http://localhost:3000

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx       # Root layout with AppProvider
│   ├── page.tsx         # Home page with three-panel layout
│   └── globals.css      # Global styles and Tailwind imports
├── components/
│   ├── MainLayout.tsx   # Header and dark mode toggle
│   ├── LeftSidebar.tsx  # Document upload and list
│   ├── CenterChat.tsx   # Chat interface with messages
│   └── RightSidebar.tsx # Match results panel
├── contexts/
│   └── AppContext.tsx   # Global state management
├── public/              # Static assets
└── package.json         # Dependencies
```

## Components

### MainLayout
- Application header with branding
- Dark mode toggle button
- Wraps main content

### LeftSidebar (Documents)
- Drag-and-drop PDF upload zone
- List of uploaded documents with status badges
- Delete document functionality

### CenterChat
- Message thread with user and AI messages
- Markdown rendering for AI responses
- Citation display for document references
- Streaming response support (simulated)
- Suggested questions for new users

### RightSidebar (Matches)
- Match cards with company and position
- Match score visualization (progress bars)
- Matching skills highlighting
- Expandable details for each match
- Demo data loader for testing

## State Management

The application uses React Context API for global state:

- **documents**: List of uploaded documents
- **messages**: Chat conversation history
- **profile**: User profile from resume parsing
- **matches**: Internship match results
- **darkMode**: UI theme preference
- **rightSidebarOpen**: Sidebar visibility state

## Features to Implement

### Next Steps (Integration with Backend)

1. **Document Upload API Integration**
   - Connect to `/api/v1/documents/upload`
   - Handle upload progress and errors
   - Update document status from backend

2. **WebSocket for Streaming**
   - Connect to `/ws/query` endpoint
   - Stream AI responses token-by-token
   - Handle connection errors gracefully

3. **Resume Upload**
   - Add resume upload component
   - Parse and display profile data
   - Edit profile functionality

4. **Match Generation**
   - Connect to `/api/v1/match` endpoint
   - Trigger matching after resume upload
   - Display real match results

5. **Search and Filters**
   - Filter matches by score, location, skills
   - Sort matches by different criteria
   - Search internships by keyword

## Styling

The application uses Tailwind CSS v4 with custom configurations:

- **Dark Mode**: Class-based dark mode (`dark:` prefix)
- **Responsive**: Mobile-first responsive design
- **Animations**: Custom animations for loading states
- **Colors**: Consistent color palette across themes

## License

MIT License
