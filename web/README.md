# Climate Fact Checker - Frontend

Next.js 15 frontend for the Climate Fact Checker application.

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Tech Stack

- **Next.js 15** with App Router and Turbopack
- **TypeScript** with strict mode
- **Tailwind CSS** for styling
- **shadcn/ui** for components
- **React Query (TanStack Query)** for data fetching
- **React Hook Form + Zod** for forms and validation
- **Axios** for API calls
- **Clerk** for authentication (to be configured)

## Project Structure

```
src/
├── app/                 # Next.js App Router pages
├── components/          # Reusable React components
│   ├── ui/             # shadcn/ui components
│   └── providers.tsx   # React Query provider
├── hooks/              # Custom React hooks
├── lib/                # Utility functions and configs
└── types/              # TypeScript type definitions
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Available Scripts

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build production application
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## API Integration

The frontend integrates with the FastAPI backend running on localhost:8000. The `ApiStatus` component on the homepage will show connection status and available notes count.

### Post UIDs
Posts are identified using URL-safe UIDs in the format `platform--platform_post_id` (e.g., `x--1234567890`). URLs automatically encode these for routing: `/notes/x--1234567890`.
