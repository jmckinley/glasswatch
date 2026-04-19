# Glasswatch Frontend

Next.js 15 frontend for the Glasswatch Patch Decision Platform.

## Features

- **Dark Theme by Default**: Required for operations teams
- **Real-time Dashboard**: Key metrics at a glance
- **Goal Management**: Create and track patching objectives
- **Vulnerability Explorer**: Browse and filter vulnerabilities
- **Patch Schedule**: Visual calendar of maintenance windows
- **AI Assistant**: Natural language interface for operations

## Tech Stack

- Next.js 15 with App Router
- TypeScript for type safety
- Tailwind CSS 4 for styling
- React 19 for UI components
- pnpm for package management

## Getting Started

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
src/
├── app/                  # Next.js app router pages
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Dashboard home page
│   └── globals.css      # Global styles
├── components/          # React components
├── lib/                 # Utilities and API client
│   └── api.ts          # Backend API client
└── hooks/              # Custom React hooks
```

## API Integration

The frontend connects to the FastAPI backend running on port 8000. All API calls include:
- Tenant header for multi-tenancy (demo mode for MVP)
- Type-safe API client in `lib/api.ts`
- Error handling with custom ApiError class

## Styling

Dark theme is the default with carefully chosen colors:
- Primary: Teal (#2dd4bf)
- Critical: Red (#f87171)
- Warning: Yellow (#fbbf24)
- Success: Green (#34d399)

All components use CSS variables for consistent theming.