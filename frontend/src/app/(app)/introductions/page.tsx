'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Users,
  Send,
  Inbox,
  CheckCircle,
  Clock,
  X,
  MessageSquare,
  Building2,
  MapPin,
  ExternalLink,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Badge,
  Avatar,
  EmptyState,
  Spinner,
  Modal,
  Textarea,
} from '@/components/ui';
import { useIntroductions } from '@/hooks/use-introductions';
import { Introduction, IntroductionSuggestion, INTRODUCTION_STATUSES } from '@/types/introduction';
import { formatRelativeTime, formatMatchScore } from '@/lib/utils';

type Tab = 'suggestions' | 'sent' | 'received';

export default function IntroductionsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('suggestions');
  const [selectedSuggestion, setSelectedSuggestion] = useState<IntroductionSuggestion | null>(null);
  const [requestMessage, setRequestMessage] = useState('');
  const [respondingTo, setRespondingTo] = useState<Introduction | null>(null);
  const [responseAction, setResponseAction] = useState<'accept' | 'decline' | null>(null);

  const { data: suggestions, isLoading: suggestionsLoading } = useIntroductions.useSuggestions();
  const { data: sentIntros, isLoading: sentLoading } = useIntroductions.useSentIntroductions();
  const { data: receivedIntros, isLoading: receivedLoading } = useIntroductions.useReceivedIntroductions();

  const requestIntroduction = useIntroductions.useRequestIntroduction();
  const respondToIntroduction = useIntroductions.useRespondToIntroduction();

  const suggestedFounders = suggestions?.matches || [];
  const sentList = sentIntros?.items || [];
  const receivedList = receivedIntros?.items || [];

  const handleRequestIntroduction = async () => {
    if (selectedSuggestion) {
      try {
        await requestIntroduction.mutateAsync({
          target_profile_id: selectedSuggestion.profile_id,
          message: requestMessage,
        });
        setSelectedSuggestion(null);
        setRequestMessage('');
      } catch (error) {
        console.error('Failed to request introduction:', error);
      }
    }
  };

  const handleRespond = async (accept: boolean) => {
    if (respondingTo) {
      try {
        await respondToIntroduction.mutateAsync({
          introductionId: respondingTo.id,
          accept,
        });
        setRespondingTo(null);
        setResponseAction(null);
      } catch (error) {
        console.error('Failed to respond:', error);
      }
    }
  };

  const tabs = [
    {
      id: 'suggestions' as Tab,
      label: 'Suggestions',
      icon: Sparkles,
      count: suggestedFounders.length,
    },
    {
      id: 'sent' as Tab,
      label: 'Sent',
      icon: Send,
      count: sentList.length,
    },
    {
      id: 'received' as Tab,
      label: 'Received',
      icon: Inbox,
      count: receivedList.filter((i) => i.status === 'pending').length,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Introductions</h1>
        <p className="text-gray-600 mt-1">
          Discover founders who match your goals and connect meaningfully.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count > 0 && (
              <span
                className={`px-2 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'suggestions' && (
        <SuggestionsTab
          suggestions={suggestedFounders}
          isLoading={suggestionsLoading}
          onConnect={setSelectedSuggestion}
        />
      )}

      {activeTab === 'sent' && (
        <SentTab introductions={sentList} isLoading={sentLoading} />
      )}

      {activeTab === 'received' && (
        <ReceivedTab
          introductions={receivedList}
          isLoading={receivedLoading}
          onRespond={(intro, action) => {
            setRespondingTo(intro);
            setResponseAction(action);
          }}
        />
      )}

      {/* Request Introduction Modal */}
      <Modal
        isOpen={!!selectedSuggestion}
        onClose={() => {
          setSelectedSuggestion(null);
          setRequestMessage('');
        }}
        title="Request Introduction"
      >
        {selectedSuggestion && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl">
              <Avatar
                src={selectedSuggestion.profile_picture_url}
                name={selectedSuggestion.display_name}
                size="lg"
              />
              <div>
                <p className="font-semibold text-gray-900">
                  {selectedSuggestion.display_name}
                </p>
                <p className="text-sm text-gray-600">
                  {selectedSuggestion.headline}
                </p>
              </div>
            </div>

            <div className="p-4 bg-primary-50 rounded-xl">
              <p className="text-sm text-primary-700">
                <strong>Why you might connect:</strong> {selectedSuggestion.match_reason}
              </p>
            </div>

            <Textarea
              label="Add a personal message (optional)"
              placeholder="Introduce yourself and explain why you'd like to connect..."
              value={requestMessage}
              onChange={(e) => setRequestMessage(e.target.value)}
              rows={4}
            />

            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedSuggestion(null);
                  setRequestMessage('');
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleRequestIntroduction}
                isLoading={requestIntroduction.isPending}
              >
                Send Request
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Respond to Introduction Modal */}
      <Modal
        isOpen={!!respondingTo}
        onClose={() => {
          setRespondingTo(null);
          setResponseAction(null);
        }}
        title={responseAction === 'accept' ? 'Accept Introduction' : 'Decline Introduction'}
      >
        {respondingTo && (
          <div className="space-y-4">
            <p className="text-gray-600">
              {responseAction === 'accept'
                ? `You're about to accept the introduction from ${respondingTo.requester?.display_name}. They'll be notified and you can start connecting.`
                : `Are you sure you want to decline this introduction from ${respondingTo.requester?.display_name}?`}
            </p>

            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setRespondingTo(null);
                  setResponseAction(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant={responseAction === 'accept' ? 'primary' : 'danger'}
                onClick={() => handleRespond(responseAction === 'accept')}
                isLoading={respondToIntroduction.isPending}
              >
                {responseAction === 'accept' ? 'Accept' : 'Decline'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// Suggestions Tab
function SuggestionsTab({
  suggestions,
  isLoading,
  onConnect,
}: {
  suggestions: IntroductionSuggestion[];
  isLoading: boolean;
  onConnect: (suggestion: IntroductionSuggestion) => void;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={Sparkles}
          title="No suggestions yet"
          description="Complete your profile and add goals to get AI-powered founder matches."
          className="py-12"
        />
      </Card>
    );
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {suggestions.map((suggestion) => (
        <SuggestionCard
          key={suggestion.profile_id}
          suggestion={suggestion}
          onConnect={() => onConnect(suggestion)}
        />
      ))}
    </div>
  );
}

// Suggestion Card
function SuggestionCard({
  suggestion,
  onConnect,
}: {
  suggestion: IntroductionSuggestion;
  onConnect: () => void;
}) {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
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
            <p className="text-sm text-gray-600 truncate mt-0.5">
              {suggestion.headline}
            </p>
            {suggestion.company_name && (
              <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                <Building2 className="w-3 h-3" />
                {suggestion.company_name}
              </p>
            )}
            {suggestion.location && (
              <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                <MapPin className="w-3 h-3" />
                {suggestion.location}
              </p>
            )}
          </div>
        </div>

        {/* Match Reason */}
        <div className="mt-4 p-3 bg-gradient-to-r from-primary-50 to-secondary-50 rounded-lg">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-primary-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-gray-700">{suggestion.match_reason}</p>
          </div>
        </div>

        {/* Shared Goals */}
        {suggestion.shared_goals && suggestion.shared_goals.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 mb-2">Shared interests:</p>
            <div className="flex flex-wrap gap-1">
              {suggestion.shared_goals.slice(0, 3).map((goal, i) => (
                <Badge key={i} variant="outline" size="sm">
                  {goal}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button onClick={onConnect} className="flex-1">
            Connect
          </Button>
          <Button variant="outline" size="sm">
            <ExternalLink className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Sent Tab
function SentTab({
  introductions,
  isLoading,
}: {
  introductions: Introduction[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (introductions.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={Send}
          title="No sent introductions"
          description="Browse suggestions to find founders you'd like to connect with."
          className="py-12"
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {introductions.map((intro) => (
        <IntroductionCard key={intro.id} introduction={intro} type="sent" />
      ))}
    </div>
  );
}

// Received Tab
function ReceivedTab({
  introductions,
  isLoading,
  onRespond,
}: {
  introductions: Introduction[];
  isLoading: boolean;
  onRespond: (intro: Introduction, action: 'accept' | 'decline') => void;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (introductions.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={Inbox}
          title="No received introductions"
          description="When other founders want to connect with you, their requests will appear here."
          className="py-12"
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {introductions.map((intro) => (
        <IntroductionCard
          key={intro.id}
          introduction={intro}
          type="received"
          onRespond={onRespond}
        />
      ))}
    </div>
  );
}

// Introduction Card
function IntroductionCard({
  introduction,
  type,
  onRespond,
}: {
  introduction: Introduction;
  type: 'sent' | 'received';
  onRespond?: (intro: Introduction, action: 'accept' | 'decline') => void;
}) {
  const person = type === 'sent' ? introduction.target : introduction.requester;

  const statusColors: Record<string, 'blue' | 'green' | 'gray' | 'red'> = {
    pending: 'blue',
    accepted: 'green',
    declined: 'red',
    completed: 'gray',
  };

  const statusIcons: Record<string, React.ElementType> = {
    pending: Clock,
    accepted: CheckCircle,
    declined: X,
    completed: CheckCircle,
  };

  const StatusIcon = statusIcons[introduction.status] || Clock;

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <Avatar
            src={person?.profile_picture_url}
            name={person?.display_name || 'Unknown'}
            size="lg"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-gray-900">
                  {person?.display_name || 'Unknown User'}
                </h3>
                <p className="text-sm text-gray-600 mt-0.5">
                  {person?.headline}
                </p>
              </div>
              <Badge variant={statusColors[introduction.status] || 'default'}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {introduction.status}
              </Badge>
            </div>

            {introduction.message && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 flex items-start gap-2">
                  <MessageSquare className="w-4 h-4 flex-shrink-0 mt-0.5 text-gray-400" />
                  {introduction.message}
                </p>
              </div>
            )}

            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-gray-400">
                {formatRelativeTime(introduction.created_at)}
              </span>

              {type === 'received' && introduction.status === 'pending' && onRespond && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onRespond(introduction, 'decline')}
                  >
                    Decline
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => onRespond(introduction, 'accept')}
                  >
                    Accept
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
