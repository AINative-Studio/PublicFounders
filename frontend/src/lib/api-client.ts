import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://publicfounders-production.up.railway.app';

/**
 * Create and configure the Axios instance
 */
function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${API_BASE_URL}/api/v1`,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds
  });

  // Request interceptor - add auth token
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Only run on client side
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor - handle errors
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      // Handle 401 Unauthorized
      if (error.response?.status === 401) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          // Don't redirect if already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      }

      // Handle network errors
      if (!error.response) {
        console.error('Network error:', error.message);
      }

      return Promise.reject(error);
    }
  );

  return client;
}

export const apiClient = createApiClient();

/**
 * Extract error message from API error response
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    // Handle string error
    if (typeof detail === 'string') {
      return detail;
    }

    // Handle validation errors array
    if (Array.isArray(detail)) {
      return detail.map((e: { msg: string }) => e.msg).join(', ');
    }

    // Handle other error formats
    if (error.response?.data?.message) {
      return error.response.data.message;
    }

    // Fallback to Axios error message
    return error.message;
  }

  // Handle generic errors
  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred';
}

/**
 * API endpoints configuration
 */
export const API_ENDPOINTS = {
  // Auth
  auth: {
    initiateLinkedIn: '/auth/linkedin/initiate',
    linkedInCallback: '/auth/linkedin/callback',
    verifyPhone: '/auth/verify-phone',
    confirmPhone: '/auth/confirm-phone',
    logout: '/auth/logout',
  },

  // Profile
  profile: {
    me: '/profile/me',
    byId: (userId: string) => `/profile/${userId}`,
    list: '/profile/',
  },

  // Goals
  goals: {
    list: '/goals',
    create: '/goals',
    byId: (id: string) => `/goals/${id}`,
    search: '/goals/search',
  },

  // Asks
  asks: {
    list: '/asks',
    create: '/asks',
    byId: (id: string) => `/asks/${id}`,
    status: (id: string) => `/asks/${id}/status`,
    search: '/asks/search',
  },

  // Posts
  posts: {
    list: '/posts',
    create: '/posts',
    byId: (id: string) => `/posts/${id}`,
    discover: '/posts/discover',
    view: (id: string) => `/posts/${id}/view`,
  },

  // Introductions
  introductions: {
    suggestions: '/introductions/suggestions',
    request: '/introductions/request',
    received: '/introductions/received',
    sent: '/introductions/sent',
    byId: (id: string) => `/introductions/${id}`,
    respond: (id: string) => `/introductions/${id}/respond`,
    complete: (id: string) => `/introductions/${id}/complete`,
    outcome: (id: string) => `/introductions/${id}/outcome`,
  },

  // Analytics
  analytics: {
    outcomes: '/outcomes/analytics',
  },
} as const;

export { API_BASE_URL };
