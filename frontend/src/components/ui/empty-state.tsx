'use client';

import { LucideIcon } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'outline';
  };
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
    >
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-gray-400" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      {description && (
        <p className="text-gray-600 max-w-sm mb-6">{description}</p>
      )}
      {action && (
        <Button
          variant={action.variant || 'primary'}
          onClick={action.onClick}
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

// Specific empty states
export function NoGoals({ onCreateGoal }: { onCreateGoal: () => void }) {
  return (
    <EmptyState
      title="No goals yet"
      description="Create your first goal to start getting matched with relevant founders and opportunities."
      action={{
        label: 'Create Goal',
        onClick: onCreateGoal,
      }}
    />
  );
}

export function NoAsks({ onCreateAsk }: { onCreateAsk: () => void }) {
  return (
    <EmptyState
      title="No asks yet"
      description="Post an ask to let others know how they can help you."
      action={{
        label: 'Create Ask',
        onClick: onCreateAsk,
      }}
    />
  );
}

export function NoPosts({ onCreatePost }: { onCreatePost: () => void }) {
  return (
    <EmptyState
      title="No posts yet"
      description="Share your journey and progress with the community."
      action={{
        label: 'Create Post',
        onClick: onCreatePost,
      }}
    />
  );
}

export function NoSuggestions() {
  return (
    <EmptyState
      title="No suggestions right now"
      description="Complete your profile and add goals to get better matches with other founders."
    />
  );
}

export function NoIntroductions() {
  return (
    <EmptyState
      title="No introductions yet"
      description="Check out suggestions to find founders you should connect with."
    />
  );
}
