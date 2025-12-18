'use client';

import { useState } from 'react';
import {
  User,
  Bell,
  Lock,
  Eye,
  Mail,
  Smartphone,
  Trash2,
  LogOut,
  Check,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Input,
  Badge,
  Modal,
} from '@/components/ui';
import { useAuthStore } from '@/store/auth-store';

type SettingsSection = 'account' | 'notifications' | 'privacy' | 'security';

export default function SettingsPage() {
  const { profile, logout } = useAuthStore();
  const [activeSection, setActiveSection] = useState<SettingsSection>('account');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  const sections = [
    { id: 'account' as SettingsSection, label: 'Account', icon: User },
    { id: 'notifications' as SettingsSection, label: 'Notifications', icon: Bell },
    { id: 'privacy' as SettingsSection, label: 'Privacy', icon: Eye },
    { id: 'security' as SettingsSection, label: 'Security', icon: Lock },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">
          Manage your account preferences and settings.
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar Navigation */}
        <div className="md:w-56 flex-shrink-0">
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center gap-3 w-full px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeSection === section.id
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <section.icon className="w-5 h-5" />
                {section.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1">
          {activeSection === 'account' && (
            <AccountSection profile={profile} />
          )}
          {activeSection === 'notifications' && <NotificationsSection />}
          {activeSection === 'privacy' && <PrivacySection />}
          {activeSection === 'security' && (
            <SecuritySection
              onDeleteAccount={() => setShowDeleteModal(true)}
              onLogout={logout}
            />
          )}
        </div>
      </div>

      {/* Delete Account Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeleteConfirmation('');
        }}
        title="Delete Account"
        description="This action cannot be undone. All your data will be permanently deleted."
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 rounded-lg">
            <p className="text-sm text-red-700">
              <strong>Warning:</strong> Deleting your account will:
            </p>
            <ul className="mt-2 text-sm text-red-600 list-disc list-inside space-y-1">
              <li>Remove all your profile information</li>
              <li>Delete all your goals, asks, and posts</li>
              <li>Cancel all pending introductions</li>
              <li>Remove you from all matches</li>
            </ul>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              Type "DELETE" to confirm
            </label>
            <Input
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
              placeholder="DELETE"
              className="mt-1.5"
            />
          </div>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteModal(false);
                setDeleteConfirmation('');
              }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={deleteConfirmation !== 'DELETE'}
            >
              Delete Account
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// Account Section
function AccountSection({ profile }: { profile: any }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Account Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-500">Email</label>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-gray-900">{profile?.email || 'Not set'}</p>
                <Badge variant="green" size="sm">Verified</Badge>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Phone</label>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-gray-900">{profile?.phone_number || 'Not set'}</p>
                {profile?.phone_verified && (
                  <Badge variant="green" size="sm">Verified</Badge>
                )}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">LinkedIn</label>
              <p className="text-gray-900 mt-1">
                {profile?.linkedin_profile_url ? 'Connected' : 'Not connected'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Connected Accounts
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#0A66C2] flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-gray-900">LinkedIn</p>
                  <p className="text-sm text-gray-500">Connected</p>
                </div>
              </div>
              <Badge variant="green">Connected</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Notifications Section
function NotificationsSection() {
  const [settings, setSettings] = useState({
    emailIntroductions: true,
    emailMatches: true,
    emailDigest: false,
    pushIntroductions: true,
    pushMessages: true,
  });

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Mail className="w-5 h-5 text-gray-400" />
            Email Notifications
          </h2>
          <div className="space-y-4">
            <ToggleSetting
              label="Introduction Requests"
              description="Get notified when someone wants to connect"
              enabled={settings.emailIntroductions}
              onToggle={() => toggleSetting('emailIntroductions')}
            />
            <ToggleSetting
              label="New Matches"
              description="Be alerted about new AI-suggested matches"
              enabled={settings.emailMatches}
              onToggle={() => toggleSetting('emailMatches')}
            />
            <ToggleSetting
              label="Weekly Digest"
              description="Receive a weekly summary of activity"
              enabled={settings.emailDigest}
              onToggle={() => toggleSetting('emailDigest')}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-gray-400" />
            Push Notifications
          </h2>
          <div className="space-y-4">
            <ToggleSetting
              label="Introduction Updates"
              description="Real-time updates on introduction requests"
              enabled={settings.pushIntroductions}
              onToggle={() => toggleSetting('pushIntroductions')}
            />
            <ToggleSetting
              label="Messages"
              description="New message notifications"
              enabled={settings.pushMessages}
              onToggle={() => toggleSetting('pushMessages')}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Privacy Section
function PrivacySection() {
  const [settings, setSettings] = useState({
    profileVisibility: 'public',
    showEmail: false,
    showPhone: false,
    allowDiscovery: true,
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Profile Visibility
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Who can see your profile?
              </label>
              <select
                value={settings.profileVisibility}
                onChange={(e) =>
                  setSettings({ ...settings, profileVisibility: e.target.value })
                }
                className="w-full h-11 mt-1.5 rounded-lg border border-gray-300 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="public">Everyone</option>
                <option value="connections">Connections Only</option>
                <option value="private">Only Me</option>
              </select>
            </div>

            <ToggleSetting
              label="Show Email"
              description="Display your email on your public profile"
              enabled={settings.showEmail}
              onToggle={() =>
                setSettings({ ...settings, showEmail: !settings.showEmail })
              }
            />
            <ToggleSetting
              label="Show Phone"
              description="Display your phone number on your profile"
              enabled={settings.showPhone}
              onToggle={() =>
                setSettings({ ...settings, showPhone: !settings.showPhone })
              }
            />
            <ToggleSetting
              label="Allow Discovery"
              description="Let AI suggest you as a match to other founders"
              enabled={settings.allowDiscovery}
              onToggle={() =>
                setSettings({ ...settings, allowDiscovery: !settings.allowDiscovery })
              }
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Security Section
function SecuritySection({
  onDeleteAccount,
  onLogout,
}: {
  onDeleteAccount: () => void;
  onLogout: () => void;
}) {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Session
          </h2>
          <p className="text-gray-600 mb-4">
            Sign out of your current session on this device.
          </p>
          <Button variant="outline" onClick={onLogout}>
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </CardContent>
      </Card>

      <Card className="border-red-200">
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-red-600 mb-4">
            Danger Zone
          </h2>
          <p className="text-gray-600 mb-4">
            Permanently delete your account and all associated data.
            This action cannot be undone.
          </p>
          <Button variant="danger" onClick={onDeleteAccount}>
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Account
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// Toggle Setting Component
function ToggleSetting({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={onToggle}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          enabled ? 'bg-primary-600' : 'bg-gray-200'
        }`}
      >
        <span
          className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );
}
