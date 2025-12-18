'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sparkles, CheckCircle, XCircle, Phone } from 'lucide-react';
import { Button, Input, Spinner } from '@/components/ui';
import { authService } from '@/lib/api/auth';
import { useAuthStore } from '@/store/auth-store';

type CallbackState =
  | 'loading'
  | 'phone_verification'
  | 'verifying_code'
  | 'success'
  | 'error';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken, setUser, setProfile } = useAuthStore();

  const [state, setState] = useState<CallbackState>('loading');
  const [error, setError] = useState<string | null>(null);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  // Handle OAuth callback - token comes directly in URL from backend redirect
  useEffect(() => {
    const handleCallback = () => {
      // Check for errors first
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (errorParam) {
        setError(errorDescription || 'Authentication was cancelled or failed.');
        setState('error');
        return;
      }

      // Get token and user info from URL (backend redirects with these)
      const token = searchParams.get('token');
      const created = searchParams.get('created') === 'true';
      const userIdParam = searchParams.get('user_id');
      const phoneVerified = searchParams.get('phone_verified') === 'true';

      if (!token) {
        setError('No authentication token received.');
        setState('error');
        return;
      }

      // Store the token and user ID
      setToken(token);
      if (userIdParam) {
        setUserId(userIdParam);
      }

      // Check if phone verification is needed
      if (created || !phoneVerified) {
        setState('phone_verification');
      } else {
        // Existing verified user - redirect to dashboard
        setState('success');
        setTimeout(() => {
          router.push('/dashboard');
        }, 1500);
      }
    };

    handleCallback();
  }, [searchParams, router, setToken]);

  // Handle phone verification request
  const handleRequestCode = async () => {
    if (!phone || phone.length < 10) {
      setPhoneError('Please enter a valid phone number');
      return;
    }

    if (!userId) {
      setPhoneError('User ID not found. Please try logging in again.');
      return;
    }

    setIsSubmitting(true);
    setPhoneError(null);

    try {
      await authService.requestPhoneVerification(userId, phone);
      setState('verifying_code');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      // Handle Pydantic validation errors (array of objects)
      if (Array.isArray(detail)) {
        const messages = detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
        setPhoneError(messages);
      } else if (typeof detail === 'object' && detail !== null) {
        setPhoneError(detail.msg || detail.message || JSON.stringify(detail));
      } else {
        setPhoneError(detail || 'Failed to send verification code. Please use E.164 format (e.g., +1234567890)');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle code verification
  const handleVerifyCode = async () => {
    if (!code || code.length !== 6) {
      setPhoneError('Please enter the 6-digit code');
      return;
    }

    if (!userId) {
      setPhoneError('User ID not found. Please try logging in again.');
      return;
    }

    setIsSubmitting(true);
    setPhoneError(null);

    try {
      await authService.confirmPhoneVerification(userId, phone, code);
      setState('success');
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      // Handle Pydantic validation errors (array of objects)
      if (Array.isArray(detail)) {
        const messages = detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
        setPhoneError(messages);
      } else if (typeof detail === 'object' && detail !== null) {
        setPhoneError(detail.msg || detail.message || JSON.stringify(detail));
      } else {
        setPhoneError(detail || 'Invalid verification code.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <span className="text-2xl font-bold text-gray-900">PublicFounders</span>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Loading State */}
          {state === 'loading' && (
            <div className="text-center py-8">
              <Spinner size="xl" className="mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900">
                Completing sign in...
              </h2>
              <p className="text-gray-600 mt-2">
                Please wait while we verify your credentials.
              </p>
            </div>
          )}

          {/* Phone Verification State */}
          {state === 'phone_verification' && (
            <div>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-4">
                  <Phone className="w-8 h-8 text-primary-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Verify your phone
                </h2>
                <p className="text-gray-600 mt-2">
                  We'll send you a verification code to confirm your identity.
                </p>
              </div>

              <div className="space-y-4">
                <Input
                  label="Phone Number"
                  type="tel"
                  placeholder="+15551234567"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  error={phoneError || undefined}
                  leftIcon={<Phone className="w-4 h-4" />}
                  helperText="Enter in E.164 format with country code (e.g., +1 for US)"
                />

                <Button
                  onClick={handleRequestCode}
                  isLoading={isSubmitting}
                  className="w-full"
                >
                  Send Verification Code
                </Button>
              </div>
            </div>
          )}

          {/* Code Verification State */}
          {state === 'verifying_code' && (
            <div>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-4">
                  <Phone className="w-8 h-8 text-primary-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Enter verification code
                </h2>
                <p className="text-gray-600 mt-2">
                  We sent a 6-digit code to {phone}
                </p>
              </div>

              <div className="space-y-4">
                <Input
                  label="Verification Code"
                  type="text"
                  inputMode="numeric"
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  error={phoneError || undefined}
                  maxLength={6}
                />

                <Button
                  onClick={handleVerifyCode}
                  isLoading={isSubmitting}
                  className="w-full"
                >
                  Verify Code
                </Button>

                <button
                  onClick={() => setState('phone_verification')}
                  className="w-full text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Use a different number
                </button>
              </div>
            </div>
          )}

          {/* Success State */}
          {state === 'success' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4 animate-in zoom-in duration-300">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">
                You're all set!
              </h2>
              <p className="text-gray-600 mt-2">
                Redirecting to your dashboard...
              </p>
            </div>
          )}

          {/* Error State */}
          {state === 'error' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                <XCircle className="w-10 h-10 text-red-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">
                Authentication failed
              </h2>
              <p className="text-gray-600 mt-2 mb-6">
                {error}
              </p>
              <Button
                onClick={() => router.push('/login')}
                className="w-full"
              >
                Try Again
              </Button>
            </div>
          )}
        </div>

        {/* Help Link */}
        <p className="text-center text-sm text-gray-500 mt-6">
          Having trouble?{' '}
          <a href="mailto:support@publicfounders.com" className="text-primary-600 hover:underline">
            Contact support
          </a>
        </p>
      </div>
    </div>
  );
}

// Loading fallback for suspense
function AuthCallbackLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <span className="text-2xl font-bold text-gray-900">PublicFounders</span>
        </div>
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center py-8">
            <Spinner size="xl" className="mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900">
              Loading...
            </h2>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<AuthCallbackLoading />}>
      <AuthCallbackContent />
    </Suspense>
  );
}
