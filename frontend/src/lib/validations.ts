import { z } from 'zod';

/**
 * Profile validation schemas
 */
export const profileUpdateSchema = z.object({
  bio: z.string().max(500, 'Bio must be 500 characters or less').optional(),
  current_focus: z.string().max(200, 'Current focus must be 200 characters or less').optional(),
  location: z.string().max(100).optional(),
  website: z.string().url('Please enter a valid URL').or(z.literal('')).optional(),
  autonomy_mode: z.enum(['suggest', 'approve', 'auto']).optional(),
  public_visibility: z.boolean().optional(),
});

export type ProfileUpdateInput = z.infer<typeof profileUpdateSchema>;

/**
 * Goal validation schemas
 */
export const goalCreateSchema = z.object({
  type: z.enum(['fundraising', 'hiring', 'growth', 'partnerships', 'learning'], {
    required_error: 'Please select a goal type',
  }),
  description: z
    .string()
    .min(20, 'Description must be at least 20 characters')
    .max(500, 'Description must be 500 characters or less'),
  priority: z
    .number()
    .min(1, 'Priority must be at least 1')
    .max(10, 'Priority must be at most 10'),
  is_active: z.boolean().default(true),
});

export const goalUpdateSchema = goalCreateSchema.partial();

export type GoalCreateInput = z.infer<typeof goalCreateSchema>;
export type GoalUpdateInput = z.infer<typeof goalUpdateSchema>;

/**
 * Ask validation schemas
 */
export const askCreateSchema = z.object({
  description: z
    .string()
    .min(10, 'Description must be at least 10 characters')
    .max(300, 'Description must be 300 characters or less'),
  goal_id: z.string().uuid('Invalid goal ID').optional().nullable(),
  urgency: z.enum(['low', 'medium', 'high'], {
    required_error: 'Please select an urgency level',
  }),
});

export const askUpdateSchema = askCreateSchema.partial().extend({
  status: z.enum(['open', 'fulfilled', 'closed']).optional(),
});

export const askStatusUpdateSchema = z.object({
  status: z.enum(['open', 'fulfilled', 'closed']),
});

export type AskCreateInput = z.infer<typeof askCreateSchema>;
export type AskUpdateInput = z.infer<typeof askUpdateSchema>;
export type AskStatusUpdateInput = z.infer<typeof askStatusUpdateSchema>;

/**
 * Post validation schemas
 */
export const postCreateSchema = z.object({
  type: z.enum(['progress', 'learning', 'milestone', 'ask'], {
    required_error: 'Please select a post type',
  }),
  content: z
    .string()
    .min(20, 'Content must be at least 20 characters')
    .max(2000, 'Content must be 2000 characters or less'),
  is_cross_posted: z.boolean().default(false),
});

export const postUpdateSchema = postCreateSchema.partial();

export type PostCreateInput = z.infer<typeof postCreateSchema>;
export type PostUpdateInput = z.infer<typeof postUpdateSchema>;

/**
 * Introduction validation schemas
 */
export const introRequestSchema = z.object({
  target_id: z.string().uuid('Invalid target user ID'),
  message: z
    .string()
    .min(20, 'Message must be at least 20 characters')
    .max(500, 'Message must be 500 characters or less'),
  context: z
    .object({
      goal_id: z.string().uuid().optional(),
      ask_id: z.string().uuid().optional(),
    })
    .optional(),
});

export const introResponseSchema = z.object({
  accept: z.boolean(),
  message: z.string().max(500).optional(),
});

export type IntroRequestInput = z.infer<typeof introRequestSchema>;
export type IntroResponseInput = z.infer<typeof introResponseSchema>;

/**
 * Outcome validation schemas
 */
export const outcomeCreateSchema = z.object({
  outcome_type: z.enum(['meeting', 'investment', 'hire', 'partnership', 'none'], {
    required_error: 'Please select an outcome type',
  }),
  feedback_text: z.string().max(1000).optional(),
  rating: z.number().min(1).max(5).optional(),
  tags: z.array(z.string()).optional(),
});

export const outcomeUpdateSchema = outcomeCreateSchema.partial();

export type OutcomeCreateInput = z.infer<typeof outcomeCreateSchema>;
export type OutcomeUpdateInput = z.infer<typeof outcomeUpdateSchema>;

/**
 * Phone verification schemas
 */
export const phoneRequestSchema = z.object({
  phone_number: z
    .string()
    .regex(/^\+[1-9]\d{1,14}$/, 'Please enter a valid phone number with country code (e.g., +1234567890)'),
});

export const phoneConfirmSchema = z.object({
  phone_number: z.string(),
  verification_code: z
    .string()
    .length(6, 'Verification code must be 6 digits')
    .regex(/^\d{6}$/, 'Verification code must contain only numbers'),
});

export type PhoneRequestInput = z.infer<typeof phoneRequestSchema>;
export type PhoneConfirmInput = z.infer<typeof phoneConfirmSchema>;
