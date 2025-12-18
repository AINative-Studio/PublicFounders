'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  Search,
  FileText,
  MoreVertical,
  Edit2,
  Trash2,
  Eye,
  Heart,
  MessageCircle,
  Share2,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Badge,
  Avatar,
  Input,
  EmptyState,
  Spinner,
  Modal,
} from '@/components/ui';
import { usePosts, useDeletePost } from '@/hooks/use-posts';
import { Post, POST_TYPES } from '@/types/post';
import { formatRelativeTime } from '@/lib/utils';
import { useAuthStore } from '@/store/auth-store';

export default function PostsPage() {
  const { profile } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [deletePost, setDeletePost] = useState<Post | null>(null);

  const { data, isLoading } = usePosts({
    type: typeFilter !== 'all' ? typeFilter : undefined,
  });

  const deletePostMutation = useDeletePost();

  const posts = data?.items || [];

  const filteredPosts = posts.filter((post) =>
    post.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    post.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async () => {
    if (deletePost) {
      try {
        await deletePostMutation.mutateAsync(deletePost.id);
        setDeletePost(null);
      } catch (error) {
        console.error('Failed to delete post:', error);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Posts</h1>
          <p className="text-gray-600 mt-1">
            Share updates and learn from other founders' journeys.
          </p>
        </div>
        <Link href="/posts/new">
          <Button>
            <Plus className="w-4 h-4 mr-1.5" />
            New Post
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search posts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftIcon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="flex gap-3">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All Types</option>
                {POST_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Posts List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : filteredPosts.length === 0 ? (
        <Card>
          <EmptyState
            icon={FileText}
            title={searchQuery || typeFilter !== 'all' ? 'No posts found' : 'No posts yet'}
            description={
              searchQuery || typeFilter !== 'all'
                ? 'Try adjusting your filters or search query.'
                : 'Share your journey and progress with the community.'
            }
            action={
              !searchQuery && typeFilter === 'all'
                ? {
                    label: 'Create Post',
                    onClick: () => window.location.href = '/posts/new',
                  }
                : undefined
            }
            className="py-12"
          />
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredPosts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              isOwner={post.author_id === profile?.id}
              onDelete={() => setDeletePost(post)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deletePost}
        onClose={() => setDeletePost(null)}
        title="Delete Post"
        description="Are you sure you want to delete this post? This action cannot be undone."
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="outline" onClick={() => setDeletePost(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            isLoading={deletePostMutation.isPending}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// Post Card Component
function PostCard({
  post,
  isOwner,
  onDelete,
}: {
  post: Post;
  isOwner: boolean;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  const typeColors: Record<string, 'blue' | 'green' | 'purple' | 'orange' | 'default'> = {
    update: 'blue',
    milestone: 'green',
    learning: 'purple',
    question: 'orange',
    announcement: 'default',
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        {/* Author Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <Avatar
              src={post.author?.profile_picture_url}
              name={post.author?.display_name || 'Unknown'}
              size="md"
            />
            <div>
              <h3 className="font-medium text-gray-900">
                {post.author?.display_name || 'Unknown Author'}
              </h3>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>{formatRelativeTime(post.created_at)}</span>
                {post.type && (
                  <>
                    <span>•</span>
                    <Badge variant={typeColors[post.type] || 'default'} size="sm">
                      {post.type}
                    </Badge>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Actions Menu */}
          {isOwner && (
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <MoreVertical className="w-4 h-4 text-gray-400" />
              </button>

              {showMenu && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowMenu(false)}
                  />
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-xl shadow-lg border border-gray-200 z-20 overflow-hidden">
                    <Link
                      href={`/posts/${post.id}/edit`}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                      Edit Post
                    </Link>
                    <button
                      onClick={() => {
                        setShowMenu(false);
                        onDelete();
                      }}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Post Content */}
        {post.title && (
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            {post.title}
          </h2>
        )}
        <p className="text-gray-700 whitespace-pre-wrap line-clamp-4">
          {post.content}
        </p>

        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {post.tags.slice(0, 5).map((tag) => (
              <span
                key={tag}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-md"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Engagement */}
        <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-100">
          <button className="flex items-center gap-1.5 text-gray-500 hover:text-primary-600 transition-colors">
            <Heart className="w-4 h-4" />
            <span className="text-sm">{post.likes_count || 0}</span>
          </button>
          <button className="flex items-center gap-1.5 text-gray-500 hover:text-primary-600 transition-colors">
            <MessageCircle className="w-4 h-4" />
            <span className="text-sm">{post.comments_count || 0}</span>
          </button>
          <button className="flex items-center gap-1.5 text-gray-500 hover:text-primary-600 transition-colors">
            <Eye className="w-4 h-4" />
            <span className="text-sm">{post.views_count || 0}</span>
          </button>
          <button className="flex items-center gap-1.5 text-gray-500 hover:text-primary-600 transition-colors ml-auto">
            <Share2 className="w-4 h-4" />
            <span className="text-sm">Share</span>
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
