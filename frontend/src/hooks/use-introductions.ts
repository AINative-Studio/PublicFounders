'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { introductionsApi } from '@/lib/api';
import type {
  IntroductionRequest,
  IntroductionResponse,
  IntroductionCompletion,
  OutcomeCreate,
  OutcomeUpdate,
  SuggestionsParams,
  IntroductionListParams,
} from '@/types';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api-client';

// Query keys
export const introKeys = {
  all: ['introductions'] as const,
  suggestions: (params?: SuggestionsParams) => [...introKeys.all, 'suggestions', params] as const,
  received: (params?: IntroductionListParams) => [...introKeys.all, 'received', params] as const,
  sent: (params?: IntroductionListParams) => [...introKeys.all, 'sent', params] as const,
  detail: (id: string) => [...introKeys.all, 'detail', id] as const,
  outcome: (id: string) => [...introKeys.all, 'outcome', id] as const,
  analytics: () => [...introKeys.all, 'analytics'] as const,
};

/**
 * Hook to get introduction suggestions
 */
export function useSuggestions(params?: SuggestionsParams) {
  return useQuery({
    queryKey: introKeys.suggestions(params),
    queryFn: () => introductionsApi.getSuggestions(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get received introductions
 */
export function useReceivedIntroductions(params?: IntroductionListParams) {
  return useQuery({
    queryKey: introKeys.received(params),
    queryFn: () => introductionsApi.getReceived(params),
    staleTime: 1 * 60 * 1000,
  });
}

/**
 * Hook to get sent introductions
 */
export function useSentIntroductions(params?: IntroductionListParams) {
  return useQuery({
    queryKey: introKeys.sent(params),
    queryFn: () => introductionsApi.getSent(params),
    staleTime: 1 * 60 * 1000,
  });
}

/**
 * Hook to get a single introduction
 */
export function useIntroduction(id: string) {
  return useQuery({
    queryKey: introKeys.detail(id),
    queryFn: () => introductionsApi.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook to request an introduction
 */
export function useRequestIntroduction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: IntroductionRequest) => introductionsApi.request(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: introKeys.sent() });
      queryClient.invalidateQueries({ queryKey: introKeys.suggestions() });
      toast.success('Introduction requested!');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to respond to an introduction
 */
export function useRespondToIntroduction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ introductionId, accept }: { introductionId: string; accept: boolean }) =>
      introductionsApi.respond(introductionId, { accept }),
    onSuccess: (_, { introductionId, accept }) => {
      queryClient.invalidateQueries({ queryKey: introKeys.received() });
      queryClient.invalidateQueries({ queryKey: introKeys.detail(introductionId) });
      toast.success(accept ? 'Introduction accepted!' : 'Introduction declined');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to mark introduction as complete
 */
export function useCompleteIntroduction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: IntroductionCompletion }) =>
      introductionsApi.complete(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: introKeys.received() });
      queryClient.invalidateQueries({ queryKey: introKeys.sent() });
      queryClient.invalidateQueries({ queryKey: introKeys.detail(id) });
      toast.success('Introduction marked as complete');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to get outcome for an introduction
 */
export function useIntroductionOutcome(introId: string) {
  return useQuery({
    queryKey: introKeys.outcome(introId),
    queryFn: () => introductionsApi.getOutcome(introId),
    enabled: !!introId,
  });
}

/**
 * Hook to create outcome
 */
export function useCreateOutcome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ introId, data }: { introId: string; data: OutcomeCreate }) =>
      introductionsApi.createOutcome(introId, data),
    onSuccess: (_, { introId }) => {
      queryClient.invalidateQueries({ queryKey: introKeys.outcome(introId) });
      queryClient.invalidateQueries({ queryKey: introKeys.detail(introId) });
      queryClient.invalidateQueries({ queryKey: introKeys.analytics() });
      toast.success('Outcome recorded!');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to update outcome
 */
export function useUpdateOutcome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ introId, data }: { introId: string; data: OutcomeUpdate }) =>
      introductionsApi.updateOutcome(introId, data),
    onSuccess: (_, { introId }) => {
      queryClient.invalidateQueries({ queryKey: introKeys.outcome(introId) });
      queryClient.invalidateQueries({ queryKey: introKeys.analytics() });
      toast.success('Outcome updated');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to get outcome analytics
 */
export function useOutcomeAnalytics() {
  return useQuery({
    queryKey: introKeys.analytics(),
    queryFn: () => introductionsApi.getAnalytics(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Namespace object for grouped access
export const useIntroductions = {
  useSuggestions,
  useReceivedIntroductions,
  useSentIntroductions,
  useRequestIntroduction,
  useRespondToIntroduction,
  useCompleteIntroduction,
  useIntroductionOutcome,
  useCreateOutcome,
  useUpdateOutcome,
  useOutcomeAnalytics,
};
