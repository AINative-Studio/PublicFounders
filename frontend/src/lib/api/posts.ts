import { apiClient, API_ENDPOINTS } from '../api-client';
import type { Post, PostCreate, PostUpdate, PostListResponse, PostDiscoveryResponse, PostListParams, PostDiscoverParams } from '@/types';

/**
 * Posts API service
 */
export const postsApi = {
  /**
   * Create a new post
   */
  create: async (data: PostCreate): Promise<Post> => {
    const response = await apiClient.post<Post>(API_ENDPOINTS.posts.create, data);
    return response.data;
  },

  /**
   * List posts with pagination and filtering
   */
  list: async (params?: PostListParams): Promise<PostListResponse> => {
    const response = await apiClient.get<PostListResponse>(API_ENDPOINTS.posts.list, {
      params,
    });
    return response.data;
  },

  /**
   * Discover relevant posts (semantic ranking)
   */
  discover: async (params?: PostDiscoverParams): Promise<PostDiscoveryResponse> => {
    const response = await apiClient.get<PostDiscoveryResponse>(API_ENDPOINTS.posts.discover, {
      params,
    });
    return response.data;
  },

  /**
   * Get a post by ID
   */
  getById: async (id: string): Promise<Post> => {
    const response = await apiClient.get<Post>(API_ENDPOINTS.posts.byId(id));
    return response.data;
  },

  /**
   * Update a post
   */
  update: async (id: string, data: PostUpdate): Promise<Post> => {
    const response = await apiClient.put<Post>(API_ENDPOINTS.posts.byId(id), data);
    return response.data;
  },

  /**
   * Delete a post
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(API_ENDPOINTS.posts.byId(id));
  },

  /**
   * Track post view
   */
  trackView: async (id: string): Promise<void> => {
    await apiClient.post(API_ENDPOINTS.posts.view(id));
  },
};
