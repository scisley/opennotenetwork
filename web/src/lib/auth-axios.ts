import axios from 'axios';
import { useAuth } from '@clerk/nextjs';
import { API_BASE_URL } from '@/lib/api';

/**
 * Create an authenticated axios instance that includes the Clerk JWT token
 */
export function useAuthenticatedApi() {
  const { getToken } = useAuth();
  
  const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 60000, // 60 seconds for long-running operations
  });

  // Add auth token to requests
  api.interceptors.request.use(async (config) => {
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

  return api;
}

/**
 * Create an axios instance for public endpoints (no auth needed)
 */
export const publicApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});