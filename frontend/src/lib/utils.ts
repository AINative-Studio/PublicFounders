import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const diffInSeconds = Math.floor((now.getTime() - then.getTime()) / 1000);

  if (diffInSeconds < 60) return 'just now';

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return diffInMinutes + ' minute' + (diffInMinutes === 1 ? '' : 's') + ' ago';

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return diffInHours + ' hour' + (diffInHours === 1 ? '' : 's') + ' ago';

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return diffInDays + ' day' + (diffInDays === 1 ? '' : 's') + ' ago';

  const diffInWeeks = Math.floor(diffInDays / 7);
  if (diffInWeeks < 4) return diffInWeeks + ' week' + (diffInWeeks === 1 ? '' : 's') + ' ago';

  const diffInMonths = Math.floor(diffInDays / 30);
  if (diffInMonths < 12) return diffInMonths + ' month' + (diffInMonths === 1 ? '' : 's') + ' ago';

  const diffInYears = Math.floor(diffInDays / 365);
  return diffInYears + ' year' + (diffInYears === 1 ? '' : 's') + ' ago';
}

export function formatMatchScore(score: number): string {
  return Math.round(score * 100) + '%';
}

export function getInitials(name: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function stringToColor(str: string): string {
  if (!str) return '#6B7280';
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = [
    '#EF4444', '#F97316', '#F59E0B', '#84CC16', '#22C55E', '#14B8A6',
    '#06B6D4', '#3B82F6', '#6366F1', '#8B5CF6', '#A855F7', '#EC4899',
  ];
  return colors[Math.abs(hash) % colors.length];
}
