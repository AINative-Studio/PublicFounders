import { apiClient, API_ENDPOINTS } from '../api-client';
import type { Ask, AskCreate, AskUpdate, AskStatusUpdate, AskListResponse, AskListParams, AskSearchParams } from '@/types';

/**
 * Asks API service
 */
export const asksApi = {
  /**
   * Create a new ask
   */
  create: async (data: AskCreate): Promise<Ask> => {
    const response = await apiClient.post<Ask>(API_ENDPOINTS.asks.create, data);
    return response.data;
  },

  /**
   * List asks with pagination and filtering
   */
  list: async (params?: AskListParams): Promise<AskListResponse> => {
    const response = await apiClient.get<AskListResponse>(API_ENDPOINTS.asks.list, {
      params,
    });
    return response.data;
  },

  /**
   * Get an ask by ID
   */
  getById: async (id: string): Promise<Ask> => {
    const response = await apiClient.get<Ask>(API_ENDPOINTS.asks.byId(id));
    return response.data;
  },

  /**
   * Update an ask
   */
  update: async (id: string, data: AskUpdate): Promise<Ask> => {
    const response = await apiClient.put<Ask>(API_ENDPOINTS.asks.byId(id), data);
    return response.data;
  },

  /**
   * Delete an ask
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(API_ENDPOINTS.asks.byId(id));
  },

  /**
   * Update ask status
   */
  updateStatus: async (id: string, data: AskStatusUpdate): Promise<Ask> => {
    const response = await apiClient.patch<Ask>(API_ENDPOINTS.asks.status(id), data);
    return response.data;
  },

  /**
   * Search asks semantically
   */
  search: async (params: AskSearchParams): Promise<AskListResponse> => {
    const response = await apiClient.get<AskListResponse>(API_ENDPOINTS.asks.search, {
      params,
    });
    return response.data;
  },
};
