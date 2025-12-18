'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, FileText, Plus, X } from 'lucide-react';
import { Button, Card, CardContent, Input, Textarea, Badge } from '@/components/ui';
import { useCreatePost } from '@/hooks/use-posts';
import { CreatePostRequest, POST_TYPES, POST_VISIBILITIES } from '@/types/post';

export default function NewPostPage() {
  const router = useRouter();
  const createPost = useCreatePost();

  const [formData, setFormData] = useState<CreatePostRequest>({
    content: '',
    title: '',
    type: 'update',
    visibility: 'public',
    tags: [],
  });

  const [tagInput, setTagInput] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.content.trim()) {
      newErrors.content = 'Content is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await createPost.mutateAsync(formData);
      router.push('/posts');
    } catch (error) {
      console.error('Failed to create post:', error);
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
          Back to Posts
        </button>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-accent-100 flex items-center justify-center">
            <FileText className="w-6 h-6 text-accent-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create New Post</h1>
            <p className="text-gray-600">
              Share your journey with the community.
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="p-6 space-y-6">
            {/* Post Type */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                What type of post is this?
              </label>
              <div className="flex flex-wrap gap-2">
                {POST_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setFormData({ ...formData, type })}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      formData.type === type
                        ? 'bg-primary-100 text-primary-700 ring-2 ring-primary-500'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Title (Optional) */}
            <Input
              label="Title (Optional)"
              placeholder="Give your post a title"
              value={formData.title || ''}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            />

            {/* Content */}
            <Textarea
              label="What's on your mind?"
              placeholder="Share an update, milestone, learning, or question with the community..."
              value={formData.content}
              onChange={(e) => {
                setFormData({ ...formData, content: e.target.value });
                setErrors({ ...errors, content: '' });
              }}
              error={errors.content}
              rows={8}
              required
            />

            {/* Visibility */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                Visibility
              </label>
              <select
                value={formData.visibility}
                onChange={(e) => setFormData({ ...formData, visibility: e.target.value as any })}
                className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {POST_VISIBILITIES.map((visibility) => (
                  <option key={visibility} value={visibility}>
                    {visibility === 'public'
                      ? 'Public - Everyone can see this'
                      : visibility === 'connections'
                      ? 'Connections Only - Only your connections can see this'
                      : 'Private - Only you can see this'}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                Tags (Optional)
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
            isLoading={createPost.isPending}
          >
            Publish Post
          </Button>
        </div>
      </form>
    </div>
  );
}
