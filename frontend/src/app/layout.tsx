import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from '@/components/providers';
import '@/styles/globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: {
    default: 'PublicFounders - Connect with Founders Who Can Help You Grow',
    template: '%s | PublicFounders',
  },
  description:
    'A semantic AI-powered founder network that intelligently connects entrepreneurs through LinkedIn data, vector embeddings, and autonomous AI agents.',
  keywords: [
    'founder network',
    'startup community',
    'entrepreneur connections',
    'AI matching',
    'build in public',
    'fundraising',
    'hiring',
    'partnerships',
  ],
  authors: [{ name: 'PublicFounders' }],
  creator: 'PublicFounders',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://publicfounders.com',
    title: 'PublicFounders - Connect with Founders Who Can Help You Grow',
    description:
      'A semantic AI-powered founder network that intelligently connects entrepreneurs.',
    siteName: 'PublicFounders',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'PublicFounders - Connect with Founders Who Can Help You Grow',
    description:
      'A semantic AI-powered founder network that intelligently connects entrepreneurs.',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#2563eb',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-gray-50 font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
