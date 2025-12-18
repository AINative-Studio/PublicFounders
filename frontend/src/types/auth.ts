export interface User {
  id: string;
  email: string;
  name: string;
  linkedin_id: string;
  profile_photo_url?: string;
  profile_picture_url?: string;
  phone_number?: string;
  phone_verified?: boolean;
  headline?: string;
  location?: string;
  created_at: string;
  updated_at?: string;
}

// Profile type is exported from ./profile.ts
// Import here for AuthResponse type
import type { Profile } from './profile';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  user: User;
  profile?: Profile;
  // Backend returns 'created' not 'is_new_user'
  created?: boolean;
  is_new_user?: boolean;
  phone_verified?: boolean;
}

export type AutonomyMode = 'suggest' | 'approve' | 'auto';

export interface IntroPreferences {
  channels?: ('linkedin' | 'email' | 'sms')[];
  availability?: 'open' | 'selective' | 'closed';
}
