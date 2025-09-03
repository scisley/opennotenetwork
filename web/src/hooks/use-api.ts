import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useAuth } from '@clerk/nextjs';
import { API_BASE_URL, API_ENDPOINTS } from '@/lib/api';
import { PublicNotesResponse, PostListResponse, PostPublic, Classifier } from '@/types/api';

// Public API (no auth needed)
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for long-running classifiers
});

// Hook to get authenticated API client
function useAuthenticatedApi() {
  const { getToken } = useAuth();
  
  const authApi = axios.create({
    baseURL: API_BASE_URL,
    timeout: 60000,
  });

  // Add auth token to requests
  authApi.interceptors.request.use(async (config) => {
    try {
      const token = await getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Failed to get auth token:', error);
    }
    return config;
  });

  return authApi;
}

export function usePublicNotes(
  status?: 'submitted' | 'accepted',
  limit = 50,
  offset = 0
) {
  return useQuery({
    queryKey: ['public-notes', { status, limit, offset }],
    queryFn: async (): Promise<PublicNotesResponse> => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      
      if (status) {
        params.append('status', status);
      }

      const response = await api.get(`${API_ENDPOINTS.public.notes}?${params}`);
      return response.data;
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health-check'],
    queryFn: async () => {
      const response = await api.get('/health');
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
    queryKey: ['public-posts', { limit, offset, search, classificationFilters }],
    queryFn: async (): Promise<PostListResponse> => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      if (search && search.trim()) {
        params.append('search', search.trim());
      }

      if (classificationFilters && Object.keys(classificationFilters).length > 0) {
        params.append('classification_filters', JSON.stringify(classificationFilters));
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
    queryKey: ['post', postUid],
    queryFn: async (): Promise<PostPublic> => {
      const response = await api.get(API_ENDPOINTS.public.postById(postUid));
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!postUid,
  });
}

// Admin API hooks for classifiers
export function useClassifiers() {
  const authApi = useAuthenticatedApi();
  
  return useQuery({
    queryKey: ['classifiers'],
    queryFn: async (): Promise<{ classifiers: Classifier[], total: number }> => {
      const response = await authApi.get('/api/admin/classifiers');
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useClassifyPost(postUid: string) {
  const queryClient = useQueryClient();
  const authApi = useAuthenticatedApi();
  
  return useMutation({
    mutationFn: async ({ classifierSlugs, force = true }: { 
      classifierSlugs?: string[], 
      force?: boolean 
    }) => {
      const params = new URLSearchParams();
      if (classifierSlugs) {
        classifierSlugs.forEach(slug => params.append('classifier_slugs', slug));
      }
      params.append('force', force.toString());
      
      const response = await authApi.post(
        `/api/admin/posts/${postUid}/classify?${params.toString()}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate the post query to refetch with new classifications
      queryClient.invalidateQueries({ queryKey: ['post', postUid] });
    },
    retry: false, // Disable retry for POST mutations to prevent duplicate operations
  });
}

// Fact Checker API hooks
export function useFactCheckers() {
  const authApi = useAuthenticatedApi();
  
  return useQuery({
    queryKey: ['fact-checkers'],
    queryFn: async () => {
      const response = await authApi.get('/api/admin/fact-checkers');
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useFactChecks(postUid: string) {
  const authApi = useAuthenticatedApi();
  
  return useQuery({
    queryKey: ['fact-checks', postUid],
    queryFn: async () => {
      const response = await authApi.get(`/api/admin/posts/${postUid}/fact-checks`);
      return response.data;
    },
    staleTime: 1000 * 60 * 1, // 1 minute - shorter because fact checks can be processing
    enabled: !!postUid,
    refetchInterval: (data) => {
      // Check if any fact checks are processing
      const hasProcessing = data?.fact_checks?.some((check: any) => 
        check.status === 'pending' || check.status === 'processing'
      );
      // Poll every 3 seconds if processing, otherwise stop
      return hasProcessing ? 3000 : false;
    },
  });
}

export function useRunFactCheck(postUid: string) {
  const queryClient = useQueryClient();
  const authApi = useAuthenticatedApi();
  
  return useMutation({
    mutationFn: async ({ factCheckerSlug, force = false }: { 
      factCheckerSlug: string, 
      force?: boolean 
    }) => {
      const params = new URLSearchParams();
      params.append('force', force.toString());
      
      const response = await authApi.post(
        `/api/admin/posts/${postUid}/fact-check/${factCheckerSlug}?${params.toString()}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate fact checks to refetch
      queryClient.invalidateQueries({ queryKey: ['fact-checks', postUid] });
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
      // Invalidate fact checks to refetch
      queryClient.invalidateQueries({ queryKey: ['fact-checks', postUid] });
    },
    retry: false,
  });
}