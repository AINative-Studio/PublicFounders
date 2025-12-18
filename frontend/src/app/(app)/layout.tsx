'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout';
import { useAuthStore } from '@/store/auth-store';
import { PageLoader } from '@/components/ui';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, isHydrated } = useAuthStore();

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/login');
    }
  }, [token, isHydrated, router]);

  // Show loading while checking auth
  if (!isHydrated) {
    return <PageLoader />;
  }

  // Redirect if not authenticated
  if (!token) {
    return <PageLoader />;
  }

  return <AppShell>{children}</AppShell>;
}
