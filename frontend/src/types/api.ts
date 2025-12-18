/**
 * Standard paginated response from the API
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

/**
 * Standard API error response
 */
export interface ApiError {
  detail: string | ValidationError[];
  type?: string;
  code?: string;
  timestamp?: string;
}

/**
 * Validation error from FastAPI
 */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * Generic list response (alternative format)
 */
export interface ListResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Standard success response
 */
export interface SuccessResponse {
  success: boolean;
  message?: string;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version?: string;
}

/**
 * Common query parameters
 */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface SearchParams {
  query: string;
  limit?: number;
  min_similarity?: number;
}

/**
 * Sort options
 */
export type SortOrder = 'asc' | 'desc';

export interface SortParams {
  sort_by?: string;
  sort_order?: SortOrder;
}
