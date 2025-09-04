import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import { API_BASE_URL, API_ENDPOINTS } from "@/lib/api";
import {
  PublicNotesResponse,
  PostListResponse,
  PostPublic,
  Classifier,
} from "@/types/api";

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
    queryFn: async (): Promise<PublicNotesResponse> => {
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

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health-check"],
    queryFn: async () => {
      const response = await api.get("/health");
      return response.data;
    },
    retry: 1,
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function usePublicPosts(
  limit = 50,
  offset = 0,
  search?: string,
  classificationFilters?: Record<string, any>
) {
  return useQuery({
    queryKey: [
      "public-posts",
      { limit, offset, search, classificationFilters },
    ],
    queryFn: async (): Promise<PostListResponse> => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
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
      const response = await api.get(
        `/api/posts/${postUid}/fact-checks`
      );
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
