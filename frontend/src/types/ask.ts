export type AskUrgency = 'low' | 'normal' | 'high';
export type AskStatus = 'open' | 'fulfilled' | 'closed';
export type AskCategory = 'advice' | 'introduction' | 'feedback' | 'resource' | 'mentorship' | 'partnership' | 'investment' | 'technical' | 'other';
export type AskVisibility = 'public' | 'connections' | 'private';

export const ASK_STATUSES: AskStatus[] = ['open', 'fulfilled', 'closed'];
export const ASK_CATEGORIES: AskCategory[] = ['advice', 'introduction', 'feedback', 'resource', 'mentorship', 'partnership', 'investment', 'technical', 'other'];
export const ASK_URGENCIES: AskUrgency[] = ['low', 'normal', 'high'];
export const ASK_VISIBILITIES: AskVisibility[] = ['public', 'connections', 'private'];

export interface Ask {
  id: string;
  user_id: string;
  goal_id?: string;
  title: string;
  description?: string;
  category: AskCategory;
  urgency: AskUrgency;
  status: AskStatus;
  visibility: AskVisibility;
  tags?: string[];
  embedding_id?: string;
  created_at: string;
  updated_at: string;
  // Populated goal data
  goal?: {
    id: string;
    type: string;
    description: string;
  };
}

export interface CreateAskRequest {
  title: string;
  description?: string;
  category: AskCategory | string;
  urgency: AskUrgency;
  visibility: AskVisibility;
  goal_id?: string;
  tags?: string[];
}

export interface UpdateAskRequest {
  title?: string;
  description?: string;
  category?: AskCategory | string;
  goal_id?: string | null;
  urgency?: AskUrgency;
  status?: AskStatus;
  visibility?: AskVisibility;
  tags?: string[];
}

export interface AskStatusUpdate {
  status: AskStatus;
}

export interface AskListResponse {
  items: Ask[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface AskListParams {
  page?: number;
  page_size?: number;
  mine_only?: boolean;
  status?: AskStatus | string;
  category?: AskCategory | string;
  urgency?: AskUrgency | string;
  goal_id?: string;
}

export interface AskSearchParams {
  query: string;
  urgency?: AskUrgency;
  status?: AskStatus;
  category?: AskCategory;
  limit?: number;
  min_similarity?: number;
}

// Urgency display configuration
export const URGENCY_CONFIG: Record<AskUrgency, { label: string; color: string; description: string }> = {
  low: { label: 'Low', color: 'gray', description: 'Anytime is fine' },
  normal: { label: 'Normal', color: 'blue', description: 'Within a few weeks' },
  high: { label: 'High', color: 'red', description: 'As soon as possible' },
};

// Status display configuration
export const STATUS_CONFIG: Record<AskStatus, { label: string; color: string }> = {
  open: { label: 'Open', color: 'blue' },
  fulfilled: { label: 'Fulfilled', color: 'green' },
  closed: { label: 'Closed', color: 'gray' },
};

// Type aliases for API compatibility
export type AskCreate = CreateAskRequest;
export type AskUpdate = UpdateAskRequest;
