import { apiClient, API_ENDPOINTS } from '../api-client';
import type { Profile, ProfileUpdate, PublicProfile, ProfileListResponse } from '@/types';

/**
 * Merge user and profile objects into a flat Profile
 */
function mergeUserAndProfile(data: { user: Record<string, any>; profile: Record<string, any> }): Profile {
  const { user, profile } = data;
  return {
    // Profile fields
    id: profile.id,
    user_id: profile.user_id || user.id,
    bio: profile.bio,
    autonomy_mode: profile.autonomy_mode,
    public_visibility: profile.public_visibility,
    intro_preferences: profile.intro_preferences,
    goals_count: profile.goals_count,
    asks_count: profile.asks_count,
    introductions_made: profile.introductions_made,
    introductions_received: profile.introductions_received,
    embedding_id: profile.embedding_id,
    current_focus: profile.current_focus,
    expertise_areas: profile.expertise_areas,
    interests: profile.interests,
    looking_for: profile.looking_for,
    // User fields (fall back to profile fields if user doesn't have them)
    email: user.email,
    phone_number: user.phone_number,
    phone_verified: user.phone_verified,
    display_name: user.name || user.full_name || user.display_name || profile.display_name || 'Unknown',
    headline: user.headline || profile.headline,
    location: user.location || profile.location,
    website_url: profile.website_url || user.website_url,
    linkedin_profile_url: user.linkedin_profile_url || profile.linkedin_profile_url,
    profile_picture_url: user.profile_picture_url || user.profile_photo_url || profile.profile_picture_url,
    company_name: profile.company_name || user.company_name,
    company_description: profile.company_description,
    company_stage: profile.company_stage,
    industry: profile.industry,
    // Timestamps
    created_at: profile.created_at || user.created_at,
    updated_at: profile.updated_at || user.updated_at,
  } as Profile;
}

/**
 * Profile API service
 */
export const profileApi = {
  /**
   * Get current user's profile
   */
  getMe: async (): Promise<Profile> => {
    const response = await apiClient.get<{ user: Record<string, any>; profile: Record<string, any> }>(API_ENDPOINTS.profile.me);
    // Backend returns { user, profile }, merge them into a flat Profile object
    return mergeUserAndProfile(response.data);
  },

  /**
   * Update current user's profile
   */
  updateMe: async (data: ProfileUpdate): Promise<Profile> => {
    const response = await apiClient.put<Profile>(API_ENDPOINTS.profile.me, data);
    return response.data;
  },

  /**
   * Get a public profile by user ID
   */
  getById: async (userId: string): Promise<PublicProfile> => {
    const response = await apiClient.get<PublicProfile>(API_ENDPOINTS.profile.byId(userId));
    return response.data;
  },

  /**
   * List public profiles
   */
  list: async (params?: { limit?: number; offset?: number }): Promise<ProfileListResponse> => {
    const response = await apiClient.get<ProfileListResponse>(API_ENDPOINTS.profile.list, {
      params,
    });
    return response.data;
  },
};
