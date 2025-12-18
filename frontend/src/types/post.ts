export type PostType = 'update' | 'milestone' | 'learning' | 'question' | 'announcement';
export type PostVisibility = 'public' | 'connections' | 'private';

export const POST_TYPES: PostType[] = ['update', 'milestone', 'learning', 'question', 'announcement'];
export const POST_VISIBILITIES: PostVisibility[] = ['public', 'connections', 'private'];

export interface PostAuthor {
  id: string;
  display_name: string;
  headline?: string;
  profile_picture_url?: string;
}

export interface Post {
  id: string;
  user_id: string;
  author_id: string;
  author?: PostAuthor;
  type: PostType;
  title?: string;
  content: string;
  visibility: PostVisibility;
  tags?: string[];
  is_cross_posted?: boolean;
  embedding_status?: string;
  views_count: number;
  likes_count: number;
  comments_count: number;
  created_at: string;
  updated_at: string;
  // Relevance score (for discover)
  relevance_score?: number;
}

export interface CreatePostRequest {
  title?: string;
  content: string;
  type: PostType;
  visibility: PostVisibility;
  tags?: string[];
  is_cross_posted?: boolean;
}

export interface UpdatePostRequest {
  title?: string;
  content?: string;
  type?: PostType;
  visibility?: PostVisibility;
  tags?: string[];
  is_cross_posted?: boolean;
}

export interface PostListResponse {
  items: Post[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface PostDiscoveryResponse {
  items: Post[];
  total: number;
}

export interface PostListParams {
  page?: number;
  page_size?: number;
  user_id?: string;
  type?: PostType | string;
}

export interface PostDiscoverParams {
  limit?: number;
  min_similarity?: number;
  recency_weight?: number;
}

// Post type display configuration
export const POST_TYPE_CONFIG: Record<PostType, { label: string; color: string; icon: string }> = {
  update: { label: 'Update', color: 'blue', icon: 'MessageSquare' },
  milestone: { label: 'Milestone', color: 'green', icon: 'Trophy' },
  learning: { label: 'Learning', color: 'purple', icon: 'Lightbulb' },
  question: { label: 'Question', color: 'orange', icon: 'HelpCircle' },
  announcement: { label: 'Announcement', color: 'primary', icon: 'Megaphone' },
};

// Type aliases for API compatibility
export type PostCreate = CreatePostRequest;
export type PostUpdate = UpdatePostRequest;
