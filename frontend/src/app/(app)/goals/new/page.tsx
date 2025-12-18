'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Target, Plus, X } from 'lucide-react';
import { Button, Card, CardContent, Input, Textarea, Badge } from '@/components/ui';
import { useCreateGoal } from '@/hooks/use-goals';
import { CreateGoalRequest, GOAL_CATEGORIES, GOAL_VISIBILITIES } from '@/types/goal';

export default function NewGoalPage() {
  const router = useRouter();
  const createGoal = useCreateGoal();

  const [formData, setFormData] = useState<CreateGoalRequest>({
    title: '',
    description: '',
    category: 'other',
    visibility: 'public',
    target_date: undefined,
    tags: [],
    seeking_help_with: [],
  });

  const [tagInput, setTagInput] = useState('');
  const [seekingInput, setSeekingInput] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    if (!formData.description?.trim()) {
      newErrors.description = 'Description is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await createGoal.mutateAsync(formData);
      router.push('/goals');
    } catch (error) {
      console.error('Failed to create goal:', error);
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
      setFormData({
        ...formData,
        tags: [...(formData.tags || []), tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setFormData({
      ...formData,
      tags: formData.tags?.filter((t) => t !== tag) || [],
    });
  };

  const addSeeking = () => {
    if (seekingInput.trim() && !formData.seeking_help_with?.includes(seekingInput.trim())) {
      setFormData({
        ...formData,
        seeking_help_with: [...(formData.seeking_help_with || []), seekingInput.trim()],
      });
      setSeekingInput('');
    }
  };

  const removeSeeking = (item: string) => {
    setFormData({
      ...formData,
      seeking_help_with: formData.seeking_help_with?.filter((s) => s !== item) || [],
    });
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Goals
        </button>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center">
            <Target className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create New Goal</h1>
            <p className="text-gray-600">
              Define what you're working towards and get matched with helpful founders.
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="p-6 space-y-6">
            {/* Title */}
            <Input
              label="Goal Title"
              placeholder="e.g., Launch MVP by Q2"
              value={formData.title}
              onChange={(e) => {
                setFormData({ ...formData, title: e.target.value });
                setErrors({ ...errors, title: '' });
              }}
              error={errors.title}
              required
            />

            {/* Description */}
            <Textarea
              label="Description"
              placeholder="Describe your goal in detail. What are you trying to achieve? What does success look like?"
              value={formData.description || ''}
              onChange={(e) => {
                setFormData({ ...formData, description: e.target.value });
                setErrors({ ...errors, description: '' });
              }}
              error={errors.description}
              rows={4}
              required
            />

            {/* Category & Visibility */}
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {GOAL_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">
                  Visibility
                </label>
                <select
                  value={formData.visibility}
                  onChange={(e) => setFormData({ ...formData, visibility: e.target.value as any })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {GOAL_VISIBILITIES.map((visibility) => (
                    <option key={visibility} value={visibility}>
                      {visibility.charAt(0).toUpperCase() + visibility.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Target Date */}
            <Input
              label="Target Date (Optional)"
              type="date"
              value={formData.target_date || ''}
              onChange={(e) => setFormData({ ...formData, target_date: e.target.value || undefined })}
            />

            {/* Tags */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                Tags
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add a tag..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                />
                <Button type="button" variant="outline" onClick={addTag}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {formData.tags && formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.tags.map((tag) => (
                    <Badge key={tag} variant="default" className="pr-1">
                      #{tag}
                      <button
                        type="button"
                        onClick={() => removeTag(tag)}
                        className="ml-1.5 p-0.5 rounded hover:bg-gray-200 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Seeking Help With */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                What help are you seeking?
              </label>
              <p className="text-xs text-gray-500 mb-2">
                This helps us match you with founders who can assist.
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g., Technical co-founder, Fundraising advice..."
                  value={seekingInput}
                  onChange={(e) => setSeekingInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addSeeking();
                    }
                  }}
                />
                <Button type="button" variant="outline" onClick={addSeeking}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {formData.seeking_help_with && formData.seeking_help_with.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.seeking_help_with.map((item) => (
                    <Badge key={item} variant="blue" className="pr-1">
                      {item}
                      <button
                        type="button"
                        onClick={() => removeSeeking(item)}
                        className="ml-1.5 p-0.5 rounded hover:bg-blue-200 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-6">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            isLoading={createGoal.isPending}
          >
            Create Goal
          </Button>
        </div>
      </form>
    </div>
  );
}
