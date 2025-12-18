'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  Search,
  Filter,
  Target,
  Calendar,
  MoreVertical,
  Edit2,
  Trash2,
  Eye,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Badge,
  Input,
  EmptyState,
  Spinner,
  Modal,
} from '@/components/ui';
import { useGoals, useDeleteGoal } from '@/hooks/use-goals';
import { Goal, GOAL_STATUSES, GOAL_CATEGORIES } from '@/types/goal';
import { formatRelativeTime } from '@/lib/utils';

export default function GoalsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [deleteGoal, setDeleteGoal] = useState<Goal | null>(null);

  const { data, isLoading } = useGoals({
    status: statusFilter !== 'all' ? statusFilter : undefined,
    category: categoryFilter !== 'all' ? categoryFilter : undefined,
  });

  const deleteGoalMutation = useDeleteGoal();

  const goals = data?.items || [];

  const filteredGoals = goals.filter((goal) =>
    goal.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    goal.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async () => {
    if (deleteGoal) {
      try {
        await deleteGoalMutation.mutateAsync(deleteGoal.id);
        setDeleteGoal(null);
      } catch (error) {
        console.error('Failed to delete goal:', error);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Goals</h1>
          <p className="text-gray-600 mt-1">
            Define your objectives and get matched with founders who can help.
          </p>
        </div>
        <Link href="/goals/new">
          <Button>
            <Plus className="w-4 h-4 mr-1.5" />
            New Goal
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search goals..."
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
                {GOAL_STATUSES.map((status) => (
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
                {GOAL_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Goals List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : filteredGoals.length === 0 ? (
        <Card>
          <EmptyState
            icon={Target}
            title={searchQuery || statusFilter !== 'all' || categoryFilter !== 'all'
              ? 'No goals found'
              : 'No goals yet'}
            description={
              searchQuery || statusFilter !== 'all' || categoryFilter !== 'all'
                ? 'Try adjusting your filters or search query.'
                : 'Create your first goal to start getting matched with relevant founders.'
            }
            action={
              !searchQuery && statusFilter === 'all' && categoryFilter === 'all'
                ? {
                    label: 'Create Goal',
                    onClick: () => window.location.href = '/goals/new',
                  }
                : undefined
            }
            className="py-12"
          />
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredGoals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onDelete={() => setDeleteGoal(goal)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteGoal}
        onClose={() => setDeleteGoal(null)}
        title="Delete Goal"
        description="Are you sure you want to delete this goal? This action cannot be undone."
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="outline" onClick={() => setDeleteGoal(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            isLoading={deleteGoalMutation.isPending}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// Goal Card Component
function GoalCard({
  goal,
  onDelete,
}: {
  goal: Goal;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  const statusColors: Record<string, 'green' | 'blue' | 'gray' | 'red'> = {
    active: 'green',
    completed: 'blue',
    paused: 'gray',
    archived: 'gray',
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
            <Target className="w-6 h-6 text-primary-600" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <Link
                  href={`/goals/${goal.id}`}
                  className="text-lg font-semibold text-gray-900 hover:text-primary-600 transition-colors"
                >
                  {goal.title}
                </Link>
                {goal.description && (
                  <p className="text-gray-600 mt-1 line-clamp-2">
                    {goal.description}
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
                        href={`/goals/${goal.id}`}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Link>
                      <Link
                        href={`/goals/${goal.id}/edit`}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                        Edit Goal
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
              <Badge variant={statusColors[goal.status] || 'default'}>
                {goal.status}
              </Badge>
              {goal.category && (
                <Badge variant="outline">
                  {goal.category.replace(/_/g, ' ')}
                </Badge>
              )}
              {goal.target_date && (
                <span className="text-sm text-gray-500 flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  Target: {new Date(goal.target_date).toLocaleDateString()}
                </span>
              )}
              <span className="text-sm text-gray-400">
                Updated {formatRelativeTime(goal.updated_at)}
              </span>
            </div>

            {/* Tags */}
            {goal.tags && goal.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {goal.tags.slice(0, 5).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-md"
                  >
                    #{tag}
                  </span>
                ))}
                {goal.tags.length > 5 && (
                  <span className="text-xs text-gray-400">
                    +{goal.tags.length - 5} more
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
