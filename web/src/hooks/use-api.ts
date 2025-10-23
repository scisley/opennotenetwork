"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import { API_BASE_URL, API_ENDPOINTS } from "@/lib/api";
import { PostListResponse, PostPublic, Classifier } from "@/types/api";

// Public API (no auth needed) - for endpoints that never require auth
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for long-running classifiers
});

// Adaptive API hook - automatically includes auth if available
// Use this for endpoints that work with or without auth (role-based responses)
function useApi() {
  const { getToken } = useAuth();

  const apiInstance = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000,
    });

    // Add auth token to requests if available
    instance.interceptors.request.use(async (config) => {
      try {
        const token = await getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch {
        // User is not logged in, continue without auth
        // This is expected behavior for public users
      }
      return config;
    });

    return instance;
  }, [getToken]);

  return apiInstance;
}

// Authenticated API hook - requires auth, fails if not authenticated
// Use this for admin-only endpoints that should never work without auth
function useAuthenticatedApi() {
  const { getToken } = useAuth();

  const authApi = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000,
    });

    // Add auth token to requests (will error if not available)
    instance.interceptors.request.use(async (config) => {
      try {
        const token = await getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        } else {
          throw new Error("No authentication token available");
        }
      } catch (error) {
        console.error("Failed to get auth token:", error);
        throw error;
      }
      return config;
    });

    return instance;
  }, [getToken]);

  return authApi;
}

export function usePublicNotes(
  status?: "submitted" | "accepted",
  limit = 50,
  offset = 0
) {
  return useQuery({
    queryKey: ["public-notes", { status, limit, offset }],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      if (status) {
        params.append("status", status);
      }

      const response = await api.get(`${API_ENDPOINTS.public.notes}?${params}`);
      return response.data;
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

export function usePublicPosts(
  limit = 50,
  offset = 0,
  search?: string,
  classificationFilters?: Record<string, any>,
  hasFactCheck?: boolean,
  hasNote?: boolean,
  factCheckStatus?: string,
  noteStatus?: string,
  createdAfter?: string,
  createdBefore?: string
) {
  return useQuery({
    queryKey: [
      "public-posts",
      {
        limit,
        offset,
        search,
        classificationFilters,
        hasFactCheck,
        hasNote,
        factCheckStatus,
        noteStatus,
        createdAfter,
        createdBefore
      },
    ],
    queryFn: async (): Promise<PostListResponse> => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        include_raw_json: "true",  // Include raw JSON for media display
      });

      if (search && search.trim()) {
        params.append("search", search.trim());
      }

      if (
        classificationFilters &&
        Object.keys(classificationFilters).length > 0
      ) {
        params.append(
          "classification_filters",
          JSON.stringify(classificationFilters)
        );
      }

      // Use fact_check_status if provided, otherwise fall back to boolean filters
      if (factCheckStatus) {
        params.append("fact_check_status", factCheckStatus);
      } else {
        if (hasFactCheck !== undefined) {
          params.append("has_fact_check", hasFactCheck.toString());
        }

        if (hasNote !== undefined) {
          params.append("has_note", hasNote.toString());
        }
      }

      // Add note_status filter
      if (noteStatus) {
        params.append("note_status", noteStatus);
      }

      if (createdAfter) {
        params.append("created_after", createdAfter);
      }

      if (createdBefore) {
        params.append("created_before", createdBefore);
      }

      const response = await api.get(`${API_ENDPOINTS.public.posts}?${params}`);
      return response.data;
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
    placeholderData: (previousData) => previousData, // Keep showing previous data while fetching
  });
}

export function usePostById(postUid: string) {
  return useQuery({
    queryKey: ["post", postUid],
    queryFn: async (): Promise<PostPublic> => {
      const response = await api.get(API_ENDPOINTS.public.postById(postUid));
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!postUid,
  });
}

// Unified classifiers hook - works for both public and authenticated users
export function useClassifiers() {
  const api = useApi();

  return useQuery({
    queryKey: ["classifiers"],
    queryFn: async (): Promise<{
      classifiers: Classifier[];
      total: number;
    }> => {
      const response = await api.get("/api/classifiers");
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Alias for backwards compatibility - remove once all components are updated
export const usePublicClassifiers = useClassifiers;

export function useClassifyPost(postUid: string) {
  const queryClient = useQueryClient();
  const authApi = useAuthenticatedApi();

  return useMutation({
    mutationFn: async ({
      classifierSlugs,
      force = true,
    }: {
      classifierSlugs?: string[];
      force?: boolean;
    }) => {
      const params = new URLSearchParams();
      if (classifierSlugs) {
        classifierSlugs.forEach((slug) =>
          params.append("classifier_slugs", slug)
        );
      }
      params.append("force", force.toString());

      const response = await authApi.post(
        `/api/admin/posts/${postUid}/classify?${params.toString()}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate the post query to refetch with new classifications
      queryClient.invalidateQueries({ queryKey: ["post", postUid] });
    },
    retry: false, // Disable retry for POST mutations to prevent duplicate operations
  });
}

// Fact Checker API hooks - using adaptive pattern
export function useFactCheckers() {
  const api = useApi();

  return useQuery({
    queryKey: ["fact-checkers"],
    queryFn: async () => {
      const response = await api.get("/api/fact-checkers");
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useFactChecks(postUid: string) {
  const api = useApi();

  return useQuery({
    queryKey: ["fact-checks", postUid],
    queryFn: async () => {
      const response = await api.get(`/api/posts/${postUid}/fact-checks`);
      return response.data;
    },
    staleTime: 1000 * 30, // 30 seconds - shorter for active polling
    enabled: !!postUid,
    refetchInterval: (query) => {
      // Access the data from the query object
      const data = query.state.data;

      // Check if any fact checks are processing
      const hasProcessing = data?.fact_checks?.some(
        (check: any) =>
          check.status === "pending" || check.status === "processing"
      );

      // Poll every 2 seconds if processing, otherwise stop
      return hasProcessing ? 2000 : false;
    },
  });
}

export function useRunFactCheck(postUid: string) {
  const queryClient = useQueryClient();
  const authApi = useAuthenticatedApi();

  return useMutation({
    mutationFn: async ({
      factCheckerSlug,
      force = false,
    }: {
      factCheckerSlug: string;
      force?: boolean;
    }) => {
      const params = new URLSearchParams();
      params.append("force", force.toString());

      const response = await authApi.post(
        `/api/admin/posts/${postUid}/fact-check/${factCheckerSlug}?${params.toString()}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch fact checks immediately
      queryClient.invalidateQueries({ queryKey: ["fact-checks", postUid] });
      queryClient.refetchQueries({ queryKey: ["fact-checks", postUid] });
    },
    retry: false,
  });
}

export function useDeleteFactCheck(postUid: string) {
  const queryClient = useQueryClient();
  const authApi = useAuthenticatedApi();

  return useMutation({
    mutationFn: async (factCheckerSlug: string) => {
      const response = await authApi.delete(
        `/api/admin/posts/${postUid}/fact-check/${factCheckerSlug}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch fact checks immediately
      queryClient.invalidateQueries({ queryKey: ["fact-checks", postUid] });
      queryClient.refetchQueries({ queryKey: ["fact-checks", postUid] });
    },
    retry: false,
  });
}

// Note Writers
export function useNoteWriters() {
  const apiInstance = useApi();

  return useQuery({
    queryKey: ["note-writers"],
    queryFn: async () => {
      const response = await apiInstance.get("/api/note-writers");
      return response.data;
    },
  });
}

// Notes for Fact Check
export function useNotes(factCheckId: string) {
  const apiInstance = useApi();

  return useQuery({
    queryKey: ["notes", factCheckId],
    queryFn: async () => {
      const response = await apiInstance.get(
        `/api/fact-checks/${factCheckId}/notes`
      );
      return response.data;
    },
    enabled: !!factCheckId,
  });
}

// Run Note Writer
export function useRunNoteWriter(factCheckId: string) {
  const authApi = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      noteWriterSlug,
      force = false,
    }: {
      noteWriterSlug: string;
      force?: boolean;
    }) => {
      const response = await authApi.post(
        `/api/admin/fact-checks/${factCheckId}/note/${noteWriterSlug}?force=${force}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", factCheckId] });
    },
  });
}

// Delete Note
export function useDeleteNote(factCheckId: string) {
  const authApi = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (noteWriterSlug: string) => {
      const response = await authApi.delete(
        `/api/admin/fact-checks/${factCheckId}/note/${noteWriterSlug}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", factCheckId] });
      queryClient.refetchQueries({ queryKey: ["notes", factCheckId] });
    },
    onError: (error: any) => {
      // Don't log 409 errors to console as they're expected and handled in the UI
      if (error?.response?.status !== 409) {
        console.error("Failed to delete note:", error);
      }
    },
    retry: false,
  });
}

// Edit Note
export function useEditNote() {
  const authApi = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      noteId,
      text,
      links,
    }: {
      noteId: string;
      text: string;
      links?: Array<{ url: string }>;
    }) => {
      const response = await authApi.patch(`/api/admin/notes/${noteId}`, {
        text,
        links,
      });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate notes queries to refresh with edited content
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

// Submit Note to X
export function useSubmitNote() {
  const authApi = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (noteId: string) => {
      const response = await authApi.post(
        `/api/admin/notes/${noteId}/submit`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate notes queries to refresh submission status
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      // Invalidate submission queue to remove submitted post
      queryClient.invalidateQueries({ queryKey: ["submission-queue"] });
    },
  });
}

// Update Submission Statuses
export function useUpdateSubmissionStatuses() {
  const authApi = useAuthenticatedApi();

  return useMutation({
    mutationFn: async () => {
      const response = await authApi.post(
        `/api/admin/submissions/update-statuses`
      );
      return response.data;
    },
  });
}

// Get Submissions Summary
export function useSubmissionsSummary() {
  const authApi = useAuthenticatedApi();

  return useQuery({
    queryKey: ["submissions", "summary"],
    queryFn: async () => {
      const response = await authApi.get(
        "/api/admin/submissions/status-summary"
      );
      return response.data;
    },
  });
}

// Get All Submissions with Details
export function useSubmissions(params?: {
  limit?: number;
  offset?: number;
  search?: string;
  status?: string;
}) {
  const authApi = useAuthenticatedApi();

  return useQuery({
    queryKey: ["submissions", params],
    queryFn: async () => {
      const response = await authApi.get("/api/admin/submissions", { params });
      return response.data;
    },
  });
}

// Get Submission Queue
export function useSubmissionQueue(params?: {
  min_score?: number;
  limit?: number;
  offset?: number;
}) {
  const authApi = useAuthenticatedApi();

  return useQuery({
    queryKey: ["submission-queue", params],
    queryFn: async () => {
      const response = await authApi.get("/api/admin/submission-queue", { params });
      return response.data;
    },
  });
}

// Get Writing Limit
export function useWritingLimit() {
  const authApi = useAuthenticatedApi();

  return useQuery({
    queryKey: ["submissions", "writing-limit"],
    queryFn: async () => {
      const response = await authApi.get("/api/admin/submissions/writing-limit");
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
