import { apiClient, API_ENDPOINTS } from '../api-client';
import type {
  Introduction,
  IntroductionSuggestion,
  IntroductionRequest,
  IntroductionResponse,
  IntroductionCompletion,
  Outcome,
  OutcomeCreate,
  OutcomeUpdate,
  OutcomeAnalytics,
  SuggestionsParams,
  IntroductionListParams,
  SuggestionsResponse,
  IntroductionListResponse,
} from '@/types';

/**
 * Introductions API service
 */
export const introductionsApi = {
  /**
   * Get introduction suggestions
   */
  getSuggestions: async (params?: SuggestionsParams): Promise<SuggestionsResponse> => {
    const response = await apiClient.get<IntroductionSuggestion[] | SuggestionsResponse>(
      API_ENDPOINTS.introductions.suggestions,
      { params }
    );
    // Handle both array and object response formats
    if (Array.isArray(response.data)) {
      return { matches: response.data, total: response.data.length };
    }
    return response.data;
  },

  /**
   * Request an introduction
   */
  request: async (data: IntroductionRequest): Promise<Introduction> => {
    const response = await apiClient.post<Introduction>(
      API_ENDPOINTS.introductions.request,
      data
    );
    return response.data;
  },

  /**
   * Get received introductions
   */
  getReceived: async (params?: IntroductionListParams): Promise<IntroductionListResponse> => {
    const response = await apiClient.get<Introduction[] | IntroductionListResponse>(
      API_ENDPOINTS.introductions.received,
      { params }
    );
    // Handle both array and object response formats
    if (Array.isArray(response.data)) {
      return {
        items: response.data,
        total: response.data.length,
        page: 1,
        page_size: response.data.length,
        has_more: false,
      };
    }
    return response.data;
  },

  /**
   * Get sent introductions
   */
  getSent: async (params?: IntroductionListParams): Promise<IntroductionListResponse> => {
    const response = await apiClient.get<Introduction[] | IntroductionListResponse>(
      API_ENDPOINTS.introductions.sent,
      { params }
    );
    // Handle both array and object response formats
    if (Array.isArray(response.data)) {
      return {
        items: response.data,
        total: response.data.length,
        page: 1,
        page_size: response.data.length,
        has_more: false,
      };
    }
    return response.data;
  },

  /**
   * Get introduction by ID
   */
  getById: async (id: string): Promise<Introduction> => {
    const response = await apiClient.get<Introduction>(
      API_ENDPOINTS.introductions.byId(id)
    );
    return response.data;
  },

  /**
   * Respond to an introduction (accept/decline)
   */
  respond: async (id: string, data: IntroductionResponse): Promise<Introduction> => {
    const response = await apiClient.put<Introduction>(
      API_ENDPOINTS.introductions.respond(id),
      data
    );
    return response.data;
  },

  /**
   * Mark introduction as complete
   */
  complete: async (id: string, data: IntroductionCompletion): Promise<Introduction> => {
    const response = await apiClient.put<Introduction>(
      API_ENDPOINTS.introductions.complete(id),
      data
    );
    return response.data;
  },

  /**
   * Record outcome for an introduction
   */
  createOutcome: async (introId: string, data: OutcomeCreate): Promise<Outcome> => {
    const response = await apiClient.post<Outcome>(
      API_ENDPOINTS.introductions.outcome(introId),
      data
    );
    return response.data;
  },

  /**
   * Get outcome for an introduction
   */
  getOutcome: async (introId: string): Promise<Outcome> => {
    const response = await apiClient.get<Outcome>(
      API_ENDPOINTS.introductions.outcome(introId)
    );
    return response.data;
  },

  /**
   * Update outcome for an introduction
   */
  updateOutcome: async (introId: string, data: OutcomeUpdate): Promise<Outcome> => {
    const response = await apiClient.patch<Outcome>(
      API_ENDPOINTS.introductions.outcome(introId),
      data
    );
    return response.data;
  },

  /**
   * Get outcome analytics
   */
  getAnalytics: async (): Promise<OutcomeAnalytics> => {
    const response = await apiClient.get<OutcomeAnalytics>(
      API_ENDPOINTS.analytics.outcomes
    );
    return response.data;
  },
};
