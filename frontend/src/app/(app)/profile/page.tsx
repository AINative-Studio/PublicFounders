'use client';

import { useState } from 'react';
import {
  MapPin,
  Briefcase,
  Link as LinkIcon,
  Edit2,
  Camera,
  Check,
  X,
  Globe,
  Users,
  Calendar,
  Building2,
} from 'lucide-react';
import { Button, Card, CardContent, Badge, Avatar, Input, Textarea, Spinner } from '@/components/ui';
import { useProfile, useUpdateProfile } from '@/hooks/use-profile';
import { INDUSTRIES, COMPANY_STAGES } from '@/types/profile';

export default function ProfilePage() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});

  const handleEdit = () => {
    setFormData({
      display_name: profile?.display_name || '',
      headline: profile?.headline || '',
      bio: profile?.bio || '',
      company_name: profile?.company_name || '',
      company_description: profile?.company_description || '',
      company_stage: profile?.company_stage || '',
      industry: profile?.industry || '',
      location: profile?.location || '',
      website_url: profile?.website_url || '',
      linkedin_profile_url: profile?.linkedin_profile_url || '',
    });
    setIsEditing(true);
  };

  const handleSave = async () => {
    try {
      await updateProfile.mutateAsync(formData);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setFormData({});
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Profile not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header Card */}
      <Card>
        <div className="relative">
          {/* Cover Image */}
          <div className="h-32 md:h-48 bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600 rounded-t-xl" />

          {/* Avatar */}
          <div className="absolute left-6 -bottom-12 md:-bottom-16">
            <div className="relative">
              <Avatar
                src={profile.profile_picture_url}
                name={profile.display_name}
                size="xl"
                className="w-24 h-24 md:w-32 md:h-32 border-4 border-white shadow-lg"
              />
              <button className="absolute bottom-0 right-0 w-8 h-8 bg-white rounded-full shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors">
                <Camera className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>

          {/* Edit Button */}
          <div className="absolute top-4 right-4">
            {isEditing ? (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  className="bg-white/90 backdrop-blur"
                >
                  <X className="w-4 h-4 mr-1" />
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  isLoading={updateProfile.isPending}
                  className="bg-white/90 backdrop-blur text-primary-600 hover:bg-white"
                >
                  <Check className="w-4 h-4 mr-1" />
                  Save
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={handleEdit}
                className="bg-white/90 backdrop-blur"
              >
                <Edit2 className="w-4 h-4 mr-1" />
                Edit Profile
              </Button>
            )}
          </div>
        </div>

        <CardContent className="pt-16 md:pt-20 pb-6">
          {isEditing ? (
            <div className="space-y-4">
              <Input
                label="Display Name"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              />
              <Input
                label="Headline"
                value={formData.headline}
                onChange={(e) => setFormData({ ...formData, headline: e.target.value })}
                placeholder="e.g., Founder @ TechStartup | Building the future of X"
              />
              <Textarea
                label="Bio"
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                rows={4}
                placeholder="Tell others about yourself..."
              />
              <Input
                label="Location"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                leftIcon={<MapPin className="w-4 h-4" />}
              />
            </div>
          ) : (
            <>
              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {profile.display_name}
                  </h1>
                  <p className="text-gray-600 mt-1">{profile.headline}</p>
                  <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-gray-500">
                    {profile.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {profile.location}
                      </span>
                    )}
                    {profile.company_name && (
                      <span className="flex items-center gap-1">
                        <Building2 className="w-4 h-4" />
                        {profile.company_name}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Joined {new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                    </span>
                  </div>
                </div>

                <div className="flex gap-3">
                  {profile.linkedin_profile_url && (
                    <a
                      href={profile.linkedin_profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-10 h-10 rounded-lg border border-gray-200 flex items-center justify-center text-gray-500 hover:text-primary-600 hover:border-primary-200 transition-colors"
                    >
                      <LinkIcon className="w-5 h-5" />
                    </a>
                  )}
                  {profile.website_url && (
                    <a
                      href={profile.website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-10 h-10 rounded-lg border border-gray-200 flex items-center justify-center text-gray-500 hover:text-primary-600 hover:border-primary-200 transition-colors"
                    >
                      <Globe className="w-5 h-5" />
                    </a>
                  )}
                </div>
              </div>

              {profile.bio && (
                <p className="text-gray-700 mt-4 leading-relaxed">{profile.bio}</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Company Information */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-gray-400" />
            Company Information
          </h2>

          {isEditing ? (
            <div className="grid md:grid-cols-2 gap-4">
              <Input
                label="Company Name"
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              />
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Company Stage</label>
                <select
                  value={formData.company_stage}
                  onChange={(e) => setFormData({ ...formData, company_stage: e.target.value })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="">Select stage...</option>
                  {COMPANY_STAGES.map((stage) => (
                    <option key={stage} value={stage}>{stage}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Industry</label>
                <select
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="w-full h-11 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="">Select industry...</option>
                  {INDUSTRIES.map((industry) => (
                    <option key={industry} value={industry}>{industry}</option>
                  ))}
                </select>
              </div>
              <Input
                label="Website"
                type="url"
                value={formData.website_url}
                onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                leftIcon={<Globe className="w-4 h-4" />}
              />
              <div className="md:col-span-2">
                <Textarea
                  label="Company Description"
                  value={formData.company_description}
                  onChange={(e) => setFormData({ ...formData, company_description: e.target.value })}
                  rows={3}
                />
              </div>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium text-gray-900">{profile.company_name || 'No company set'}</h3>
                {profile.company_description && (
                  <p className="text-gray-600 mt-2 text-sm">{profile.company_description}</p>
                )}
              </div>
              <div className="space-y-3">
                {profile.industry && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gray-500">Industry:</span>
                    <Badge variant="blue">{profile.industry}</Badge>
                  </div>
                )}
                {profile.company_stage && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gray-500">Stage:</span>
                    <Badge variant="purple">{profile.company_stage}</Badge>
                  </div>
                )}
                {profile.website_url && (
                  <div className="flex items-center gap-2 text-sm">
                    <Globe className="w-4 h-4 text-gray-400" />
                    <a
                      href={profile.website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline"
                    >
                      {profile.website_url.replace(/^https?:\/\//, '')}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Card */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-400" />
            Network Stats
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-xl">
              <p className="text-2xl font-bold text-primary-600">
                {profile.goals_count || 0}
              </p>
              <p className="text-sm text-gray-600 mt-1">Goals</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-xl">
              <p className="text-2xl font-bold text-secondary-600">
                {profile.asks_count || 0}
              </p>
              <p className="text-sm text-gray-600 mt-1">Asks</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-xl">
              <p className="text-2xl font-bold text-accent-600">
                {profile.introductions_made || 0}
              </p>
              <p className="text-sm text-gray-600 mt-1">Intros Made</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-xl">
              <p className="text-2xl font-bold text-green-600">
                {profile.introductions_received || 0}
              </p>
              <p className="text-sm text-gray-600 mt-1">Intros Received</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
