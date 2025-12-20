import { apiClient, API_ENDPOINTS, API_BASE_URL } from '../api-client';
import type { AuthResponse } from '@/types';

/**
 * Authentication API service
 */
export const authApi = {
  /**
   * Initiate LinkedIn OAuth flow
   * Redirects to LinkedIn authorization page
   */
  initiateLinkedIn: () => {
    // Use configured redirect URI, or construct from current origin
    const redirectUri =
      process.env.NEXT_PUBLIC_LINKEDIN_REDIRECT_URI ||
      (typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : 'http://localhost:3000/auth/callback');
    const initiateUrl = `${API_BASE_URL}/api/v1${API_ENDPOINTS.auth.initiateLinkedIn}?redirect_uri=${encodeURIComponent(redirectUri)}`;

    if (typeof window !== 'undefined') {
      window.location.href = initiateUrl;
    }
  },

  /**
   * Handle LinkedIn OAuth callback
   * Exchanges authorization code for JWT token
   */
  handleCallback: async (code: string, state?: string): Promise<AuthResponse> => {
    const params: Record<string, string> = { code };
    if (state) {
      params.state = state;
    }

    const response = await apiClient.get<AuthResponse>(API_ENDPOINTS.auth.linkedInCallback, {
      params,
    });
    return response.data;
  },

  /**
   * Request phone verification code
   */
  requestPhoneVerification: async (userId: string, phoneNumber: string): Promise<void> => {
    await apiClient.post(API_ENDPOINTS.auth.verifyPhone, {
      phone_number: phoneNumber,
    }, {
      params: { user_id: userId },
    });
  },

  /**
   * Confirm phone verification code
   */
  confirmPhoneVerification: async (
    userId: string,
    phoneNumber: string,
    verificationCode: string
  ): Promise<void> => {
    await apiClient.post(API_ENDPOINTS.auth.confirmPhone, {
      phone_number: phoneNumber,
      verification_code: verificationCode,
    }, {
      params: { user_id: userId },
    });
  },

  /**
   * Logout current user
   */
  logout: async (): Promise<void> => {
    await apiClient.post(API_ENDPOINTS.auth.logout);
  },
};

// Alias for backwards compatibility
export const authService = authApi;
