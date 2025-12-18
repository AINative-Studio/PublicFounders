'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { asksApi } from '@/lib/api';
import type { AskCreate, AskUpdate, AskStatusUpdate, AskListParams, AskSearchParams } from '@/types';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api-client';

// Query keys
export const askKeys = {
  all: ['asks'] as const,
  lists: () => [...askKeys.all, 'list'] as const,
  list: (params?: AskListParams) => [...askKeys.lists(), params] as const,
  details: () => [...askKeys.all, 'detail'] as const,
  detail: (id: string) => [...askKeys.details(), id] as const,
  search: (params: AskSearchParams) => [...askKeys.all, 'search', params] as const,
};

/**
 * Hook to list asks
 */
export function useAsks(params?: AskListParams) {
  return useQuery({
    queryKey: askKeys.list(params),
    queryFn: () => asksApi.list(params),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Hook to get a single ask
 */
export function useAsk(id: string) {
  return useQuery({
    queryKey: askKeys.detail(id),
    queryFn: () => asksApi.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook to create an ask
 */
export function useCreateAsk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AskCreate) => asksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: askKeys.lists() });
      toast.success('Ask created successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to update an ask
 */
export function useUpdateAsk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AskUpdate }) => asksApi.update(id, data),
    onSuccess: (updatedAsk, { id }) => {
      queryClient.setQueryData(askKeys.detail(id), updatedAsk);
      queryClient.invalidateQueries({ queryKey: askKeys.lists() });
      toast.success('Ask updated successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to delete an ask
 */
export function useDeleteAsk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => asksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: askKeys.lists() });
      toast.success('Ask deleted successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to update ask status
 */
export function useUpdateAskStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AskStatusUpdate }) => asksApi.updateStatus(id, data),
    onSuccess: (updatedAsk, { id }) => {
      queryClient.setQueryData(askKeys.detail(id), updatedAsk);
      queryClient.invalidateQueries({ queryKey: askKeys.lists() });
      toast.success('Status updated successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to search asks
 */
export function useSearchAsks(params: AskSearchParams, enabled = true) {
  return useQuery({
    queryKey: askKeys.search(params),
    queryFn: () => asksApi.search(params),
    enabled: enabled && !!params.query,
    staleTime: 30 * 1000,
  });
}
