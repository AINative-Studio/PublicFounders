import { AutonomyMode, IntroPreferences } from './auth';

export type CompanyStage = 'idea' | 'pre-seed' | 'seed' | 'series-a' | 'series-b' | 'growth' | 'public';

export const COMPANY_STAGES: CompanyStage[] = ['idea', 'pre-seed', 'seed', 'series-a', 'series-b', 'growth', 'public'];

export const INDUSTRIES: string[] = [
  'Technology',
  'Healthcare',
  'Finance',
  'E-commerce',
  'Education',
  'Real Estate',
  'Manufacturing',
  'Media & Entertainment',
  'Consumer Goods',
  'Transportation',
  'Energy',
  'Agriculture',
  'Other',
];

export interface Profile {
  id: string;
  user_id: string;
  email?: string;
  phone_number?: string;
  phone_verified?: boolean;
  display_name: string;
  headline?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  linkedin_profile_url?: string;
  profile_picture_url?: string;
  company_name?: string;
  company_description?: string;
  company_stage?: CompanyStage;
  industry?: string;
  autonomy_mode?: AutonomyMode;
  public_visibility?: boolean;
  intro_preferences?: IntroPreferences;
  goals_count?: number;
  asks_count?: number;
  introductions_made?: number;
  introductions_received?: number;
  embedding_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  display_name?: string;
  headline?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  linkedin_profile_url?: string;
  company_name?: string;
  company_description?: string;
  company_stage?: CompanyStage;
  industry?: string;
  autonomy_mode?: AutonomyMode;
  public_visibility?: boolean;
  intro_preferences?: IntroPreferences;
}

export interface PublicProfile {
  id: string;
  user_id: string;
  display_name: string;
  headline?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  profile_picture_url?: string;
  company_name?: string;
  company_stage?: CompanyStage;
  industry?: string;
  created_at: string;
}

export interface ProfileListResponse {
  profiles: PublicProfile[];
  total: number;
  limit: number;
  offset: number;
}

// Legacy types for backwards compatibility
export interface FounderProfile extends Profile {}
