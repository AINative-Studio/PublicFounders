export type IntroStatus = 'pending' | 'accepted' | 'declined' | 'completed' | 'expired';
export type OutcomeType = 'meeting' | 'investment' | 'hire' | 'partnership' | 'none';
export type MatchType = 'goal_based' | 'ask_based' | 'all';

export const INTRODUCTION_STATUSES: IntroStatus[] = ['pending', 'accepted', 'declined', 'completed', 'expired'];

export interface IntroductionSuggestion {
  profile_id: string;
  display_name: string;
  headline?: string;
  profile_picture_url?: string;
  company_name?: string;
  location?: string;
  match_score: number;
  match_reason: string;
  match_type?: MatchType;
  shared_goals?: string[];
}

export interface SuggestionsResponse {
  matches: IntroductionSuggestion[];
  total: number;
}

export interface IntroductionProfile {
  id: string;
  display_name: string;
  headline?: string;
  profile_picture_url?: string;
  company_name?: string;
}

export interface Introduction {
  id: string;
  requester_id: string;
  target_id: string;
  connector_id?: string;
  status: IntroStatus;
  message?: string;
  response_message?: string;
  context?: {
    goal_id?: string;
    ask_id?: string;
  };
  created_at: string;
  updated_at: string;
  // Populated user data
  requester?: IntroductionProfile;
  target?: IntroductionProfile;
  outcome?: Outcome;
}

export interface IntroductionListResponse {
  items: Introduction[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface IntroductionRequest {
  target_profile_id: string;
  message?: string;
  connector_id?: string;
  context?: {
    goal_id?: string;
    ask_id?: string;
  };
}

export interface IntroductionResponse {
  accept: boolean;
  message?: string;
}

export interface IntroductionCompletion {
  outcome: string;
  notes?: string;
}

export interface Outcome {
  id: string;
  introduction_id: string;
  user_id: string;
  outcome_type: OutcomeType;
  feedback_text?: string;
  rating?: number;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export interface OutcomeCreate {
  outcome_type: OutcomeType;
  feedback_text?: string;
  rating?: number;
  tags?: string[];
}

export interface OutcomeUpdate {
  outcome_type?: OutcomeType;
  feedback_text?: string;
  rating?: number;
  tags?: string[];
}

export interface OutcomeAnalytics {
  total_introductions: number;
  completed_introductions: number;
  success_rate: number;
  outcome_breakdown: Record<OutcomeType, number>;
  average_rating: number;
  top_tags: string[];
}

export interface SuggestionsParams {
  limit?: number;
  min_score?: number;
  match_type?: MatchType;
}

export interface IntroductionListParams {
  status?: IntroStatus;
  limit?: number;
  offset?: number;
}

// Status display configuration
export const INTRO_STATUS_CONFIG: Record<IntroStatus, { label: string; color: string }> = {
  pending: { label: 'Pending', color: 'accent' },
  accepted: { label: 'Accepted', color: 'success' },
  declined: { label: 'Declined', color: 'error' },
  completed: { label: 'Completed', color: 'primary' },
  expired: { label: 'Expired', color: 'gray' },
};

// Outcome type display configuration
export const OUTCOME_TYPE_CONFIG: Record<OutcomeType, { label: string; color: string; icon: string }> = {
  meeting: { label: 'Had a Meeting', color: 'primary', icon: 'Calendar' },
  investment: { label: 'Investment', color: 'success', icon: 'DollarSign' },
  hire: { label: 'Made a Hire', color: 'secondary', icon: 'UserPlus' },
  partnership: { label: 'Partnership', color: 'accent', icon: 'Handshake' },
  none: { label: 'No Outcome', color: 'gray', icon: 'X' },
};
