'use client';

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { postsApi } from '@/lib/api';
import type { PostCreate, PostUpdate, PostListParams, PostDiscoverParams } from '@/types';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api-client';

// Query keys
export const postKeys = {
  all: ['posts'] as const,
  lists: () => [...postKeys.all, 'list'] as const,
  list: (params?: PostListParams) => [...postKeys.lists(), params] as const,
  details: () => [...postKeys.all, 'detail'] as const,
  detail: (id: string) => [...postKeys.details(), id] as const,
  discover: (params?: PostDiscoverParams) => [...postKeys.all, 'discover', params] as const,
  infinite: (params?: PostListParams) => [...postKeys.all, 'infinite', params] as const,
};

/**
 * Hook to list posts
 */
export function usePosts(params?: PostListParams) {
  return useQuery({
    queryKey: postKeys.list(params),
    queryFn: () => postsApi.list(params),
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

/**
 * Hook for infinite scroll posts (feed)
 */
export function useInfinitePosts(params?: Omit<PostListParams, 'page'>) {
  return useInfiniteQuery({
    queryKey: postKeys.infinite(params),
    queryFn: ({ pageParam = 1 }) => postsApi.list({ ...params, page: pageParam }),
    getNextPageParam: (lastPage) => {
      if (lastPage.has_more) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 1 * 60 * 1000,
  });
}

/**
 * Hook to discover relevant posts
 */
export function useDiscoverPosts(params?: PostDiscoverParams) {
  return useQuery({
    queryKey: postKeys.discover(params),
    queryFn: () => postsApi.discover(params),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Hook to get a single post
 */
export function usePost(id: string) {
  return useQuery({
    queryKey: postKeys.detail(id),
    queryFn: () => postsApi.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook to create a post
 */
export function useCreatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PostCreate) => postsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: postKeys.lists() });
      queryClient.invalidateQueries({ queryKey: postKeys.infinite() });
      toast.success('Post published successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to update a post
 */
export function useUpdatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PostUpdate }) => postsApi.update(id, data),
    onSuccess: (updatedPost, { id }) => {
      queryClient.setQueryData(postKeys.detail(id), updatedPost);
      queryClient.invalidateQueries({ queryKey: postKeys.lists() });
      queryClient.invalidateQueries({ queryKey: postKeys.infinite() });
      toast.success('Post updated successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to delete a post
 */
export function useDeletePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => postsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: postKeys.lists() });
      queryClient.invalidateQueries({ queryKey: postKeys.infinite() });
      toast.success('Post deleted successfully');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook to track post view
 */
export function useTrackPostView() {
  return useMutation({
    mutationFn: (id: string) => postsApi.trackView(id),
    // Silent - no toast
  });
}
