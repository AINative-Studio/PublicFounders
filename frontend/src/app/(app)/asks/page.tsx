'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  Search,
  HelpCircle,
  MoreVertical,
  Edit2,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
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
import { useAsks, useDeleteAsk } from '@/hooks/use-asks';
import { Ask, ASK_STATUSES, ASK_CATEGORIES } from '@/types/ask';
import { formatRelativeTime } from '@/lib/utils';

export default function AsksPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [deleteAsk, setDeleteAsk] = useState<Ask | null>(null);

  const { data, isLoading } = useAsks({
    status: statusFilter !== 'all' ? statusFilter : undefined,
    category: categoryFilter !== 'all' ? categoryFilter : undefined,
  });

  const deleteAskMutation = useDeleteAsk();

  const asks = data?.items || [];

  const filteredAsks = asks.filter((ask) =>
    ask.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ask.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async () => {
    if (deleteAsk) {
      try {
        await deleteAskMutation.mutateAsync(deleteAsk.id);
        setDeleteAsk(null);
      } catch (error) {
        console.error('Failed to delete ask:', error);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Asks</h1>
          <p className="text-gray-600 mt-1">
            Request help from the community and offer your expertise.
          </p>
        </div>
        <Link href="/asks/new">
          <Button>
            <Plus className="w-4 h-4 mr-1.5" />
            New Ask
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search asks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftIcon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="flex gap-3">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All Statuses</option>
                {ASK_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </option>
                ))}
              </select>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All Categories</option>
                {ASK_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Asks List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : filteredAsks.length === 0 ? (
        <Card>
          <EmptyState
            icon={HelpCircle}
            title={searchQuery || statusFilter !== 'all' || categoryFilter !== 'all'
              ? 'No asks found'
              : 'No asks yet'}
            description={
              searchQuery || statusFilter !== 'all' || categoryFilter !== 'all'
                ? 'Try adjusting your filters or search query.'
                : 'Post an ask to let others know how they can help you.'
            }
            action={
              !searchQuery && statusFilter === 'all' && categoryFilter === 'all'
                ? {
                    label: 'Create Ask',
                    onClick: () => window.location.href = '/asks/new',
                  }
                : undefined
            }
            className="py-12"
          />
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredAsks.map((ask) => (
            <AskCard
              key={ask.id}
              ask={ask}
              onDelete={() => setDeleteAsk(ask)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteAsk}
        onClose={() => setDeleteAsk(null)}
        title="Delete Ask"
        description="Are you sure you want to delete this ask? This action cannot be undone."
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="outline" onClick={() => setDeleteAsk(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            isLoading={deleteAskMutation.isPending}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// Ask Card Component
function AskCard({
  ask,
  onDelete,
}: {
  ask: Ask;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  const statusColors: Record<string, 'blue' | 'green' | 'gray'> = {
    open: 'blue',
    fulfilled: 'green',
    closed: 'gray',
  };

  const statusIcons: Record<string, React.ElementType> = {
    open: Clock,
    fulfilled: CheckCircle,
    closed: HelpCircle,
  };

  const StatusIcon = statusIcons[ask.status] || HelpCircle;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-secondary-100 flex items-center justify-center flex-shrink-0">
            <HelpCircle className="w-6 h-6 text-secondary-600" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <Link
                  href={`/asks/${ask.id}`}
                  className="text-lg font-semibold text-gray-900 hover:text-primary-600 transition-colors"
                >
                  {ask.title}
                </Link>
                {ask.description && (
                  <p className="text-gray-600 mt-1 line-clamp-2">
                    {ask.description}
                  </p>
                )}
              </div>

              {/* Actions Menu */}
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
                        href={`/asks/${ask.id}`}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Link>
                      <Link
                        href={`/asks/${ask.id}/edit`}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                        Edit Ask
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
            </div>

            {/* Meta Info */}
            <div className="flex flex-wrap items-center gap-3 mt-4">
              <Badge variant={statusColors[ask.status] || 'default'}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {ask.status}
              </Badge>
              {ask.category && (
                <Badge variant="outline">
                  {ask.category.replace(/_/g, ' ')}
                </Badge>
              )}
              {ask.urgency && ask.urgency !== 'normal' && (
                <Badge variant={ask.urgency === 'high' ? 'red' : 'yellow'}>
                  {ask.urgency} priority
                </Badge>
              )}
              <span className="text-sm text-gray-400">
                Posted {formatRelativeTime(ask.created_at)}
              </span>
            </div>

            {/* Tags */}
            {ask.tags && ask.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {ask.tags.slice(0, 5).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-md"
                  >
                    #{tag}
                  </span>
                ))}
                {ask.tags.length > 5 && (
                  <span className="text-xs text-gray-400">
                    +{ask.tags.length - 5} more
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
