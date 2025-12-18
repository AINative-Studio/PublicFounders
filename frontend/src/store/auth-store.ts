'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, Profile } from '@/types';

interface AuthState {
  // State
  token: string | null;
  user: User | null;
  profile: Profile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isHydrated: boolean;

  // Actions
  setToken: (token: string) => void;
  setAuth: (token: string, user: User, profile: Profile) => void;
  setUser: (user: User) => void;
  setProfile: (profile: Profile) => void;
  updateProfile: (updates: Partial<Profile>) => void;
  setLoading: (isLoading: boolean) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      token: null,
      user: null,
      profile: null,
      isAuthenticated: false,
      isLoading: true,
      isHydrated: false,

      // Set token only
      setToken: (token) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
        set({
          token,
          isAuthenticated: true,
        });
      },

      // Set full auth state after login
      setAuth: (token, user, profile) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
        set({
          token,
          user,
          profile,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      // Update user
      setUser: (user) => {
        set({ user });
      },

      // Update profile
      setProfile: (profile) => {
        set({ profile });
      },

      // Partial profile update
      updateProfile: (updates) => {
        const currentProfile = get().profile;
        if (currentProfile) {
          set({
            profile: { ...currentProfile, ...updates },
          });
        }
      },

      // Set loading state
      setLoading: (isLoading) => {
        set({ isLoading });
      },

      // Logout
      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
        set({
          token: null,
          user: null,
          profile: null,
          isAuthenticated: false,
          isLoading: false,
        });
        // Redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      },

      // Hydrate state from storage
      hydrate: () => {
        const state = get();
        if (state.token) {
          set({ isAuthenticated: true, isLoading: false, isHydrated: true });
        } else {
          set({ isLoading: false, isHydrated: true });
        }
      },
    }),
    {
      name: 'publicfounders-auth',
      storage: createJSONStorage(() => {
        if (typeof window !== 'undefined') {
          return localStorage;
        }
        // Return a dummy storage for SSR
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        };
      }),
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        profile: state.profile,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isLoading = false;
          state.isHydrated = true;
        }
      },
    }
  )
);

// Selector hooks for better performance
export const useUser = () => useAuthStore((state) => state.user);
export const useProfile = () => useAuthStore((state) => state.profile);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useIsHydrated = () => useAuthStore((state) => state.isHydrated);
