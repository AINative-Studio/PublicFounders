'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileApi } from '@/lib/api';
import { useAuthStore } from '@/store/auth-store';
import type { ProfileUpdate } from '@/types';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api-client';

// Query keys
export const profileKeys = {
  all: ['profile'] as const,
  me: () => [...profileKeys.all, 'me'] as const,
  byId: (id: string) => [...profileKeys.all, 'user', id] as const,
  list: (params?: { limit?: number; offset?: number }) => [...profileKeys.all, 'list', params] as const,
};

/**
 * Hook to get current user's profile
 */
export function useMyProfile() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: profileKeys.me(),
    queryFn: profileApi.getMe,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Alias for useMyProfile
export const useProfile = useMyProfile;

/**
 * Hook to update current user's profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const updateStoreProfile = useAuthStore((state) => state.updateProfile);

  return useMutation({
    mutationFn: (data: ProfileUpdate) => profileApi.updateMe(data),
    onSuccess: (updatedProfile) => {
      // Update cache
      queryClient.setQueryData(profileKeys.me(), updatedProfile);
      // Update store
      updateStoreProfile(updatedProfile);
      toast.success('Profile updated successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to get a public profile by ID
 */
export function usePublicProfile(userId: string) {
  return useQuery({
    queryKey: profileKeys.byId(userId),
    queryFn: () => profileApi.getById(userId),
    enabled: !!userId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to list public profiles
 */
export function usePublicProfiles(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: profileKeys.list(params),
    queryFn: () => profileApi.list(params),
    staleTime: 5 * 60 * 1000,
  });
}
