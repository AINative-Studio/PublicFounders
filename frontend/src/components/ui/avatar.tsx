'use client';

import Image from 'next/image';
import { cn, getInitials, stringToColor } from '@/lib/utils';

export interface AvatarProps {
  src?: string | null;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  showOnline?: boolean;
  className?: string;
}

export function Avatar({
  src,
  name,
  size = 'md',
  showOnline = false,
  className,
}: AvatarProps) {
  const sizes = {
    xs: { container: 'w-6 h-6', text: 'text-[10px]', online: 'w-1.5 h-1.5 border' },
    sm: { container: 'w-8 h-8', text: 'text-xs', online: 'w-2 h-2 border' },
    md: { container: 'w-10 h-10', text: 'text-sm', online: 'w-2.5 h-2.5 border-2' },
    lg: { container: 'w-12 h-12', text: 'text-base', online: 'w-3 h-3 border-2' },
    xl: { container: 'w-16 h-16', text: 'text-lg', online: 'w-3.5 h-3.5 border-2' },
    '2xl': { container: 'w-24 h-24', text: 'text-2xl', online: 'w-4 h-4 border-2' },
  };

  const sizeConfig = sizes[size];
  const initials = getInitials(name);
  const bgColor = stringToColor(name);

  // Check if custom size classes are provided in className
  const hasCustomSize = className && /w-\d+/.test(className);

  return (
    <div className={cn('relative inline-flex', className)}>
      {src ? (
        <div
          className={cn(
            'relative rounded-full overflow-hidden bg-gray-200',
            hasCustomSize ? 'w-full h-full' : sizeConfig.container
          )}
        >
          <Image
            src={src}
            alt={name}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 96px, 128px"
            unoptimized={src.includes('licdn.com')} // LinkedIn images need unoptimized
          />
        </div>
      ) : (
        <div
          className={cn(
            'flex items-center justify-center rounded-full text-white font-medium',
            hasCustomSize ? 'w-full h-full' : sizeConfig.container,
            sizeConfig.text,
            bgColor
          )}
        >
          {initials}
        </div>
      )}
      {showOnline && (
        <span
          className={cn(
            'absolute bottom-0 right-0 bg-green-500 rounded-full border-white',
            sizeConfig.online
          )}
        />
      )}
    </div>
  );
}

// Avatar group for showing multiple avatars
export interface AvatarGroupProps {
  avatars: Array<{ src?: string | null; name: string }>;
  max?: number;
  size?: AvatarProps['size'];
  className?: string;
}

export function AvatarGroup({
  avatars,
  max = 4,
  size = 'md',
  className,
}: AvatarGroupProps) {
  const visibleAvatars = avatars.slice(0, max);
  const remainingCount = avatars.length - max;

  const overlapSizes = {
    xs: '-ml-1.5',
    sm: '-ml-2',
    md: '-ml-2.5',
    lg: '-ml-3',
    xl: '-ml-4',
    '2xl': '-ml-6',
  };

  return (
    <div className={cn('flex items-center', className)}>
      {visibleAvatars.map((avatar, index) => (
        <div
          key={index}
          className={cn(
            'relative ring-2 ring-white rounded-full',
            index > 0 && overlapSizes[size]
          )}
          style={{ zIndex: visibleAvatars.length - index }}
        >
          <Avatar src={avatar.src} name={avatar.name} size={size} />
        </div>
      ))}
      {remainingCount > 0 && (
        <div
          className={cn(
            'flex items-center justify-center rounded-full bg-gray-100 text-gray-600 font-medium ring-2 ring-white',
            overlapSizes[size],
            size === 'xs' && 'w-6 h-6 text-[10px]',
            size === 'sm' && 'w-8 h-8 text-xs',
            size === 'md' && 'w-10 h-10 text-sm',
            size === 'lg' && 'w-12 h-12 text-base',
            size === 'xl' && 'w-16 h-16 text-lg',
            size === '2xl' && 'w-24 h-24 text-2xl'
          )}
        >
          +{remainingCount}
        </div>
      )}
    </div>
  );
}
