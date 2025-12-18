'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, HelpCircle, Plus, X } from 'lucide-react';
import { Button, Card, CardContent, Input, Textarea, Badge } from '@/components/ui';
import { useCreateAsk } from '@/hooks/use-asks';
import { CreateAskRequest, ASK_CATEGORIES, ASK_URGENCIES, ASK_VISIBILITIES } from '@/types/ask';

export default function NewAskPage() {
  const router = useRouter();
  const createAsk = useCreateAsk();

  const [formData, setFormData] = useState<CreateAskRequest>({
    title: '',
    description: '',
    category: 'advice',
    urgency: 'normal',
    visibility: 'public',
    tags: [],
  });

  const [tagInput, setTagInput] = useState('');
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
      await createAsk.mutateAsync(formData);
      router.push('/asks');
    } catch (error) {
      console.error('Failed to create ask:', error);
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

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Asks
        </button>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-secondary-100 flex items-center justify-center">
            <HelpCircle className="w-6 h-6 text-secondary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create New Ask</h1>
            <p className="text-gray-600">
              Let the community know how they can help you.
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
              label="What do you need help with?"
              placeholder="e.g., Looking for intro to investors in FinTech"
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
              label="More details"
              placeholder="Provide context about your ask. What specifically are you looking for? What's your current situation?"
              value={formData.description || ''}
              onChange={(e) => {
                setFormData({ ...formData, description: e.target.value });
                setErrors({ ...errors, description: '' });
              }}
              error={errors.description}
              rows={5}
              required
            />

            {/* Category, Urgency, Visibility */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {ASK_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">
                  Urgency
                </label>
                <select
                  value={formData.urgency}
                  onChange={(e) => setFormData({ ...formData, urgency: e.target.value as any })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {ASK_URGENCIES.map((urgency) => (
                    <option key={urgency} value={urgency}>
                      {urgency.charAt(0).toUpperCase() + urgency.slice(1)}
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
                  {ASK_VISIBILITIES.map((visibility) => (
                    <option key={visibility} value={visibility}>
                      {visibility.charAt(0).toUpperCase() + visibility.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Tags */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                Tags (Optional)
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Add tags to help others find your ask.
              </p>
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

            {/* Tips */}
            <div className="bg-blue-50 rounded-xl p-4">
              <h4 className="font-medium text-blue-900 mb-2">Tips for a great ask:</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Be specific about what you need</li>
                <li>• Explain why you need this help</li>
                <li>• Mention any relevant context or constraints</li>
                <li>• Consider what you can offer in return</li>
              </ul>
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
            isLoading={createAsk.isPending}
          >
            Post Ask
          </Button>
        </div>
      </form>
    </div>
  );
}
