export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Public endpoints
  public: {
    notes: '/api/public/notes',
    noteById: (postUid: string) => `/api/public/notes/${encodeURIComponent(postUid)}`,
    posts: '/api/public/posts',
    postById: (postUid: string) => `/api/public/posts/${encodeURIComponent(postUid)}`,
  },
  // Admin endpoints (will require auth in the future)
  admin: {
    ingest: '/api/admin/ingest',
    posts: '/api/admin/posts',
    postById: (postUid: string) => `/api/admin/posts/${encodeURIComponent(postUid)}`,
    classify: (postUid: string) => `/api/admin/posts/${encodeURIComponent(postUid)}/classify`,
    drafts: (postUid: string) => `/api/admin/posts/${encodeURIComponent(postUid)}/drafts`,
    reconcile: '/api/admin/submissions/reconcile',
  },
} as const;