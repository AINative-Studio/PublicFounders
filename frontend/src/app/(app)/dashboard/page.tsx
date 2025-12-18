'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Target,
  HelpCircle,
  Users,
  TrendingUp,
  ArrowRight,
  Plus,
  Sparkles,
  Calendar,
  Eye,
} from 'lucide-react';
import { Button, Card, CardContent, Badge, Avatar, SkeletonCard, EmptyState } from '@/components/ui';
import { useProfile } from '@/hooks/use-profile';
import { useGoals } from '@/hooks/use-goals';
import { useAsks } from '@/hooks/use-asks';
import { useIntroductions } from '@/hooks/use-introductions';
import { formatRelativeTime, formatMatchScore } from '@/lib/utils';

export default function DashboardPage() {
  const { data: profile, isLoading: profileLoading } = useProfile();
  const { data: goalsData, isLoading: goalsLoading } = useGoals();
  const { data: asksData, isLoading: asksLoading } = useAsks();
  const { data: suggestions, isLoading: suggestionsLoading } = useIntroductions.useSuggestions();

  const goals = goalsData?.items || [];
  const asks = asksData?.items || [];
  const suggestedFounders = suggestions?.matches || [];

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back{profile?.display_name ? `, ${profile.display_name.split(' ')[0]}` : ''}!
          </h1>
          <p className="text-gray-600 mt-1">
            Here's what's happening with your network today.
          </p>
        </div>
        <div className="flex gap-3">
          <Link href="/goals/new">
            <Button variant="outline" size="sm">
              <Plus className="w-4 h-4 mr-1.5" />
              New Goal
            </Button>
          </Link>
          <Link href="/asks/new">
            <Button size="sm">
              <Plus className="w-4 h-4 mr-1.5" />
              New Ask
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Target}
          label="Active Goals"
          value={goals.filter(g => g.status === 'active').length}
          trend="+2 this week"
          color="primary"
        />
        <StatCard
          icon={HelpCircle}
          label="Open Asks"
          value={asks.filter(a => a.status === 'open').length}
          trend="3 responses"
          color="secondary"
        />
        <StatCard
          icon={Users}
          label="Introductions"
          value={12}
          trend="+5 this month"
          color="accent"
        />
        <StatCard
          icon={TrendingUp}
          label="Match Score"
          value="92%"
          trend="Top 10%"
          color="green"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* AI Suggestions - Takes 2 columns */}
        <div className="lg:col-span-2">
          <Card>
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-900">AI Suggestions</h2>
                    <p className="text-sm text-gray-500">Founders you should meet</p>
                  </div>
                </div>
                <Link href="/introductions">
                  <Button variant="ghost" size="sm">
                    View All
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </Link>
              </div>
            </div>

            <CardContent className="p-0">
              {suggestionsLoading ? (
                <div className="p-6 space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-gray-200 animate-pulse" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-200 rounded w-1/3 animate-pulse" />
                        <div className="h-3 bg-gray-200 rounded w-1/2 animate-pulse" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : suggestedFounders.length === 0 ? (
                <EmptyState
                  title="No suggestions yet"
                  description="Complete your profile and add goals to get AI-powered matches."
                  className="py-12"
                />
              ) : (
                <div className="divide-y divide-gray-100">
                  {suggestedFounders.slice(0, 4).map((suggestion) => (
                    <div
                      key={suggestion.profile_id}
                      className="p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start gap-4">
                        <Avatar
                          src={suggestion.profile_picture_url}
                          name={suggestion.display_name}
                          size="lg"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-gray-900 truncate">
                              {suggestion.display_name}
                            </h3>
                            <Badge variant="green" size="sm">
                              {formatMatchScore(suggestion.match_score)}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 truncate">
                            {suggestion.headline}
                          </p>
                          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                            {suggestion.match_reason}
                          </p>
                        </div>
                        <Link href={`/introductions?suggest=${suggestion.profile_id}`}>
                          <Button size="sm">
                            Connect
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Activity Feed */}
        <div>
          <Card>
            <div className="p-6 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Recent Activity</h2>
            </div>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-100">
                <ActivityItem
                  icon={Users}
                  title="New introduction"
                  description="Sarah wants to connect"
                  time="2 hours ago"
                  color="primary"
                />
                <ActivityItem
                  icon={Eye}
                  title="Profile viewed"
                  description="5 founders viewed your profile"
                  time="5 hours ago"
                  color="secondary"
                />
                <ActivityItem
                  icon={Target}
                  title="Goal matched"
                  description="Found 3 founders with similar goals"
                  time="1 day ago"
                  color="accent"
                />
                <ActivityItem
                  icon={HelpCircle}
                  title="Ask response"
                  description="John offered to help with fundraising"
                  time="2 days ago"
                  color="green"
                />
              </div>
              <div className="p-4 border-t border-gray-100">
                <Button variant="ghost" className="w-full" size="sm">
                  View All Activity
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Goals & Asks Row */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent Goals */}
        <Card>
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Your Goals</h2>
              <Link href="/goals">
                <Button variant="ghost" size="sm">
                  View All
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
          <CardContent className="p-0">
            {goalsLoading ? (
              <div className="p-6">
                <SkeletonCard />
              </div>
            ) : goals.length === 0 ? (
              <EmptyState
                title="No goals yet"
                description="Set your first goal to start getting matched."
                action={{
                  label: 'Create Goal',
                  onClick: () => window.location.href = '/goals/new',
                }}
                className="py-8"
              />
            ) : (
              <div className="divide-y divide-gray-100">
                {goals.slice(0, 3).map((goal) => (
                  <Link
                    key={goal.id}
                    href={`/goals/${goal.id}`}
                    className="block p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-gray-900 truncate">
                          {goal.title}
                        </h3>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {goal.description}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant={goal.status === 'active' ? 'green' : 'default'} size="sm">
                            {goal.status}
                          </Badge>
                          {goal.target_date && (
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {new Date(goal.target_date).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Asks */}
        <Card>
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Your Asks</h2>
              <Link href="/asks">
                <Button variant="ghost" size="sm">
                  View All
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
          <CardContent className="p-0">
            {asksLoading ? (
              <div className="p-6">
                <SkeletonCard />
              </div>
            ) : asks.length === 0 ? (
              <EmptyState
                title="No asks yet"
                description="Post an ask to let others know how they can help."
                action={{
                  label: 'Create Ask',
                  onClick: () => window.location.href = '/asks/new',
                }}
                className="py-8"
              />
            ) : (
              <div className="divide-y divide-gray-100">
                {asks.slice(0, 3).map((ask) => (
                  <Link
                    key={ask.id}
                    href={`/asks/${ask.id}`}
                    className="block p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-gray-900 truncate">
                          {ask.title}
                        </h3>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {ask.description}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant={ask.status === 'open' ? 'blue' : 'default'} size="sm">
                            {ask.status}
                          </Badge>
                          <Badge variant="outline" size="sm">
                            {ask.category}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend: string;
  color: 'primary' | 'secondary' | 'accent' | 'green';
}) {
  const colors = {
    primary: 'bg-primary-100 text-primary-600',
    secondary: 'bg-secondary-100 text-secondary-600',
    accent: 'bg-accent-100 text-accent-600',
    green: 'bg-green-100 text-green-600',
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500 mt-2">{trend}</p>
    </Card>
  );
}

// Activity Item Component
function ActivityItem({
  icon: Icon,
  title,
  description,
  time,
  color,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  time: string;
  color: 'primary' | 'secondary' | 'accent' | 'green';
}) {
  const colors = {
    primary: 'bg-primary-100 text-primary-600',
    secondary: 'bg-secondary-100 text-secondary-600',
    accent: 'bg-accent-100 text-accent-600',
    green: 'bg-green-100 text-green-600',
  };

  return (
    <div className="p-4 flex items-start gap-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colors[color]}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 text-sm">{title}</p>
        <p className="text-sm text-gray-600 truncate">{description}</p>
      </div>
      <span className="text-xs text-gray-400 flex-shrink-0">{time}</span>
    </div>
  );
}
