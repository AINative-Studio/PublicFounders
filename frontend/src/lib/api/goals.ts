import { apiClient, API_ENDPOINTS } from '../api-client';
import type { Goal, GoalCreate, GoalUpdate, GoalListResponse, GoalListParams, GoalSearchParams } from '@/types';

/**
 * Goals API service
 */
export const goalsApi = {
  /**
   * Create a new goal
   */
  create: async (data: GoalCreate): Promise<Goal> => {
    const response = await apiClient.post<Goal>(API_ENDPOINTS.goals.create, data);
    return response.data;
  },

  /**
   * List goals with pagination and filtering
   */
  list: async (params?: GoalListParams): Promise<GoalListResponse> => {
    const response = await apiClient.get<GoalListResponse>(API_ENDPOINTS.goals.list, {
      params,
    });
    return response.data;
  },

  /**
   * Get a goal by ID
   */
  getById: async (id: string): Promise<Goal> => {
    const response = await apiClient.get<Goal>(API_ENDPOINTS.goals.byId(id));
    return response.data;
  },

  /**
   * Update a goal
   */
  update: async (id: string, data: GoalUpdate): Promise<Goal> => {
    const response = await apiClient.put<Goal>(API_ENDPOINTS.goals.byId(id), data);
    return response.data;
  },

  /**
   * Delete a goal
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(API_ENDPOINTS.goals.byId(id));
  },

  /**
   * Search goals semantically
   */
  search: async (params: GoalSearchParams): Promise<GoalListResponse> => {
    const response = await apiClient.get<GoalListResponse>(API_ENDPOINTS.goals.search, {
      params,
    });
    return response.data;
  },
};
