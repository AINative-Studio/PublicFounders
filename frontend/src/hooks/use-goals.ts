'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { goalsApi } from '@/lib/api';
import type { GoalCreate, GoalUpdate, GoalListParams, GoalSearchParams } from '@/types';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api-client';

// Query keys
export const goalKeys = {
  all: ['goals'] as const,
  lists: () => [...goalKeys.all, 'list'] as const,
  list: (params?: GoalListParams) => [...goalKeys.lists(), params] as const,
  details: () => [...goalKeys.all, 'detail'] as const,
  detail: (id: string) => [...goalKeys.details(), id] as const,
  search: (params: GoalSearchParams) => [...goalKeys.all, 'search', params] as const,
};

/**
 * Hook to list goals
 */
export function useGoals(params?: GoalListParams) {
  return useQuery({
    queryKey: goalKeys.list(params),
    queryFn: () => goalsApi.list(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook to get a single goal
 */
export function useGoal(id: string) {
  return useQuery({
    queryKey: goalKeys.detail(id),
    queryFn: () => goalsApi.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook to create a goal
 */
export function useCreateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: GoalCreate) => goalsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal created successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to update a goal
 */
export function useUpdateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) => goalsApi.update(id, data),
    onSuccess: (updatedGoal, { id }) => {
      queryClient.setQueryData(goalKeys.detail(id), updatedGoal);
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal updated successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to delete a goal
 */
export function useDeleteGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => goalsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal deleted successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to search goals
 */
export function useSearchGoals(params: GoalSearchParams, enabled = true) {
  return useQuery({
    queryKey: goalKeys.search(params),
    queryFn: () => goalsApi.search(params),
    enabled: enabled && !!params.query,
    staleTime: 30 * 1000, // 30 seconds
  });
}
