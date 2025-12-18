export type GoalStatus = 'active' | 'completed' | 'paused' | 'archived';
export type GoalCategory = 'fundraising' | 'hiring' | 'growth' | 'partnerships' | 'product' | 'marketing' | 'operations' | 'learning' | 'other';
export type GoalVisibility = 'public' | 'connections' | 'private';

export const GOAL_STATUSES: GoalStatus[] = ['active', 'completed', 'paused', 'archived'];
export const GOAL_CATEGORIES: GoalCategory[] = ['fundraising', 'hiring', 'growth', 'partnerships', 'product', 'marketing', 'operations', 'learning', 'other'];
export const GOAL_VISIBILITIES: GoalVisibility[] = ['public', 'connections', 'private'];

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  category: GoalCategory;
  status: GoalStatus;
  visibility: GoalVisibility;
  target_date?: string;
  tags?: string[];
  seeking_help_with?: string[];
  embedding_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateGoalRequest {
  title: string;
  description?: string;
  category: GoalCategory | string;
  visibility: GoalVisibility;
  target_date?: string;
  tags?: string[];
  seeking_help_with?: string[];
}

export interface UpdateGoalRequest {
  title?: string;
  description?: string;
  category?: GoalCategory | string;
  status?: GoalStatus;
  visibility?: GoalVisibility;
  target_date?: string;
  tags?: string[];
  seeking_help_with?: string[];
}

export interface GoalListResponse {
  items: Goal[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface GoalListParams {
  page?: number;
  page_size?: number;
  status?: GoalStatus | string;
  category?: GoalCategory | string;
}

export interface GoalSearchParams {
  query: string;
  category?: GoalCategory | string;
  limit?: number;
  min_similarity?: number;
}

// Goal category display configuration
export const GOAL_CATEGORY_CONFIG: Record<GoalCategory, { label: string; color: string }> = {
  fundraising: { label: 'Fundraising', color: 'primary' },
  hiring: { label: 'Hiring', color: 'secondary' },
  growth: { label: 'Growth', color: 'accent' },
  partnerships: { label: 'Partnerships', color: 'purple' },
  product: { label: 'Product', color: 'blue' },
  marketing: { label: 'Marketing', color: 'orange' },
  operations: { label: 'Operations', color: 'gray' },
  learning: { label: 'Learning', color: 'cyan' },
  other: { label: 'Other', color: 'gray' },
};

// Type aliases for API compatibility
export type GoalCreate = CreateGoalRequest;
export type GoalUpdate = UpdateGoalRequest;
