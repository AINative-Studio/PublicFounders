'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Linkedin, ArrowRight, Users, Target, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui';
import { authService } from '@/lib/api/auth';

const features = [
  {
    icon: Users,
    title: 'AI-Powered Matching',
    description: 'Get introduced to founders who share your goals and can help you grow.',
  },
  {
    icon: Target,
    title: 'Goal-Oriented Network',
    description: 'Connect based on what you\'re working towards, not just who you know.',
  },
  {
    icon: Lightbulb,
    title: 'Meaningful Introductions',
    description: 'Every connection is curated to create real value for both founders.',
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLinkedInLogin = () => {
    setIsLoading(true);
    setError(null);

    try {
      // This function redirects directly to LinkedIn OAuth
      authService.initiateLinkedIn();
    } catch (err) {
      setError('Failed to initiate login. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel - Branding & Features */}
      <div className="hidden lg:flex lg:flex-1 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 p-12 flex-col justify-between">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">PublicFounders</span>
          </div>

          {/* Headline */}
          <div className="mt-16">
            <h1 className="text-4xl font-bold text-white leading-tight">
              Connect with founders<br />
              who get it.
            </h1>
            <p className="mt-4 text-lg text-white/80 max-w-md">
              Join a community of ambitious founders building in public. Get matched
              with people who can help you reach your goals.
            </p>
          </div>

          {/* Features */}
          <div className="mt-12 space-y-6">
            {features.map((feature, index) => (
              <div key={index} className="flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-white/20 backdrop-blur flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{feature.title}</h3>
                  <p className="text-sm text-white/70 mt-1">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Testimonial */}
        <div className="mt-auto pt-12">
          <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
            <p className="text-white/90 italic">
              "PublicFounders helped me find my co-founder. The AI matching is incredible
              at understanding what you actually need."
            </p>
            <div className="mt-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/20" />
              <div>
                <p className="text-white font-medium">Sarah Chen</p>
                <p className="text-white/60 text-sm">Founder, TechStartup</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-12 justify-center">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">PublicFounders</span>
          </div>

          {/* Welcome Text */}
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Welcome back</h2>
            <p className="text-gray-600 mt-2">
              Sign in to continue building your network
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* LinkedIn Login Button */}
          <Button
            onClick={handleLinkedInLogin}
            isLoading={isLoading}
            className="w-full h-12 bg-[#0A66C2] hover:bg-[#004182] text-white"
          >
            {!isLoading && <Linkedin className="w-5 h-5 mr-2" />}
            Continue with LinkedIn
          </Button>

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-white text-gray-500">
                Secure authentication
              </span>
            </div>
          </div>

          {/* Info */}
          <div className="bg-gray-50 rounded-xl p-6">
            <h3 className="font-semibold text-gray-900 mb-3">Why LinkedIn?</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start gap-2">
                <ArrowRight className="w-4 h-4 mt-0.5 text-primary-500 flex-shrink-0" />
                <span>Verify your professional identity</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="w-4 h-4 mt-0.5 text-primary-500 flex-shrink-0" />
                <span>Import your work experience automatically</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="w-4 h-4 mt-0.5 text-primary-500 flex-shrink-0" />
                <span>Connect with your existing network</span>
              </li>
            </ul>
          </div>

          {/* Terms */}
          <p className="mt-8 text-center text-xs text-gray-500">
            By continuing, you agree to our{' '}
            <a href="/terms" className="text-primary-600 hover:underline">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="text-primary-600 hover:underline">
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
