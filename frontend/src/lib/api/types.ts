// Espelha `backend/app/models/enums.py` e `backend/app/schemas/*.py`.
// Manter em sincronia manualmente: qualquer campo novo no backend precisa
// aparecer aqui para a interface saber o formato dos dados.

export type ContentFormat = "REEL" | "IMAGE_POST" | "CAROUSEL" | "STORY";

export type ContentObjective = "SELL" | "ATTRACT" | "BRAND";

export type ContentStatus =
  | "IDEA"
  | "DRAFT"
  | "REVIEW"
  | "APPROVED"
  | "SCHEDULED"
  | "PUBLISHED"
  | "REJECTED"
  | "ARCHIVED";

export type IdeaStatus = "AVAILABLE" | "USED" | "DISCARDED";

export type AssetKind =
  | "PRODUCT_PHOTO"
  | "PLACE_PHOTO"
  | "TEAM_PHOTO"
  | "LOGO"
  | "REFERENCE"
  | "AI_GENERATED"
  | "MODEL_PHOTO"
  | "VIDEO_GENERATED"
  | "THUMBNAIL"
  | "OTHER";

export type AssetStatus = "PENDING_UPLOAD" | "READY" | "FAILED";

export type ContentAssetRole = "COVER" | "SLIDE" | "SCENE" | "REFERENCE" | "PRIMARY_VIDEO" | "THUMBNAIL";

export type VersionAuthor = "USER" | "AI" | "SYSTEM";

export type RegenerationScope =
  | "FULL"
  | "TITLE"
  | "CONCEPT"
  | "HOOK"
  | "BODY"
  | "CAPTION"
  | "HASHTAGS"
  | "CTA"
  | "IMAGE"
  | "VIDEO";

export type JobKind =
  | "IDEATION"
  | "CONTENT_PRODUCTION"
  | "CONTENT_REGENERATION"
  | "CONTENT_CREATION"
  | "CAMPAIGN_GENERATION"
  | "CAMPAIGN_REGENERATION"
  | "TALENT_GENERATION"
  | "ASSET_ANALYSIS";

export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

// ------------------------------------------------------------------- auth --

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface SessionResponse {
  user: UserRead;
  business_id: string | null;
  has_business: boolean;
}

// --------------------------------------------------------------- business --

export interface ContentPreferences {
  preferred_formats: ContentFormat[];
  preferred_categories: string[];
  avoided_categories: string[];
  posts_per_week: number;
  language: string;
  emoji_usage: string;
  forbidden_topics: string[];
  extra_guidelines: string;
  default_cta?: string;
  whatsapp?: string;
}

export interface BusinessRead {
  id: string;
  name: string;
  segment: string;
  description: string | null;
  target_audience: string | null;
  location: string | null;
  brand_voice: string | null;
  additional_info: string | null;
  instagram_handle: string | null;
  website: string | null;
  differentiators: string[];
  objectives: string[];
  content_preferences: ContentPreferences;
  completeness_score: number;
  created_at: string;
  updated_at: string;
}

export interface BusinessCreatePayload {
  name: string;
  segment: string;
  description?: string | null;
  target_audience?: string | null;
  location?: string | null;
  brand_voice?: string | null;
  additional_info?: string | null;
  instagram_handle?: string | null;
  website?: string | null;
  differentiators?: string[];
  objectives?: string[];
  content_preferences?: Partial<ContentPreferences> | null;
}

export type BusinessUpdatePayload = Partial<BusinessCreatePayload>;

// ---------------------------------------------------------------- catalog --

export interface ProductRead {
  id: string;
  business_id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number | null;
  currency: string;
  highlights: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductPayload {
  name: string;
  description?: string | null;
  category?: string | null;
  price?: number | null;
  currency?: string;
  highlights?: string[];
  is_active?: boolean;
}

export interface ServiceRead {
  id: string;
  business_id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number | null;
  currency: string;
  duration_minutes: number | null;
  deliverables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ServicePayload {
  name: string;
  description?: string | null;
  category?: string | null;
  price?: number | null;
  currency?: string;
  duration_minutes?: number | null;
  deliverables?: string[];
  is_active?: boolean;
}

// ----------------------------------------------------------------- assets --

export interface AssetRead {
  id: string;
  business_id: string;
  product_id: string | null;
  service_id: string | null;
  kind: AssetKind;
  status: AssetStatus;
  original_filename: string;
  mime_type: string;
  size_bytes: number | null;
  width: number | null;
  height: number | null;
  duration_seconds?: number | null;
  title: string | null;
  alt_text: string | null;
  tags: string[];
  ai_analysis: Record<string, unknown> | null;
  created_at: string;
  url: string | null;
}

export interface AssetUploadResponse {
  asset_id: string;
  upload_url: string;
  method: string;
  headers: Record<string, string>;
  expires_in: number;
}

// ------------------------------------------------------------------ ideas --

export interface ContentIdeaRead {
  id: string;
  business_id: string;
  title: string;
  concept: string;
  objective: string;
  category: string;
  suggested_format: ContentFormat;
  rationale: string | null;
  hook_suggestion: string | null;
  audience_note: string | null;
  relevance_score: number;
  referenced_products: string[];
  referenced_services: string[];
  status: IdeaStatus;
  job_id: string | null;
  created_at: string;
}

// --------------------------------------------------------------- contents --

export interface ContentAssetRead {
  asset: AssetRead;
  role: ContentAssetRole;
  position: number;
}

export interface ContentRead {
  id: string;
  business_id: string;
  idea_id: string | null;
  campaign_id?: string | null;
  product_id?: string | null;
  title: string;
  concept: string | null;
  objective: string | null;
  category: string | null;
  format: ContentFormat;
  status: ContentStatus;
  caption: string | null;
  cta: string | null;
  hashtags: string[];
  payload: Record<string, unknown>;
  planned_date: string | null;
  published_at: string | null;
  current_version: number;
  created_at: string;
  updated_at: string;
  assets: ContentAssetRead[];
  allowed_transitions: ContentStatus[];
}

export interface ContentSummary {
  id: string;
  title: string;
  format: ContentFormat;
  status: ContentStatus;
  category: string | null;
  planned_date: string | null;
  current_version: number;
  updated_at: string;
}

export interface ContentActionResponse {
  content: ContentRead;
  job_id: string | null;
}

export interface ContentVersionRead {
  id: string;
  content_id: string;
  version: number;
  author: VersionAuthor;
  change_reason: string | null;
  ai_instruction: string | null;
  regeneration_scope: RegenerationScope | null;
  snapshot: Record<string, unknown>;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ------------------------------------------------------------------- jobs --

export interface JobRead {
  id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  stage?: string | null;
  provider: string | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobAccepted {
  job_id: string;
  status: JobStatus;
  kind: JobKind;
}

// --------------------------------------------------------------------- ai --

export interface CategoryRead {
  key: string;
  label: string;
  description: string;
  objective: string;
  recommended_formats: ContentFormat[];
  weight: number;
}

export interface TaxonomyRead {
  version: number;
  categories: CategoryRead[];
}

export interface FormatRead {
  format: ContentFormat;
  label: string;
  body_label: string;
  payload_schema: Record<string, unknown>;
}

export interface AICapabilitiesRead {
  provider: string;
  model: string;
  supports_vision: boolean;
  image_provider: string;
  image_model: string;
  video_provider?: string;
  video_model?: string;
  execution_mode: string;
  taxonomy_version: number;
  default_idea_count: number;
  max_ideas_per_run: number;
}

// --------------------------------------------------------------- dashboard --

export interface ContentCounters {
  total: number;
  by_status: Record<string, number>;
  by_format: Record<string, number>;
  created_last_30_days: number;
  ideas_available: number;
  assets_ready: number;
}

export interface CalendarCoverage {
  horizon_days: number;
  scheduled_days: number;
  coverage_percent: number;
  next_gap_date: string | null;
  target_posts_per_week: number;
}

export interface NextAction {
  kind: string;
  title: string;
  description: string;
  cta_label: string;
  content_id: string | null;
  idea_id: string | null;
  href?: string | null;
}

export interface QuickCreateItem {
  id: string;
  kind: "product" | "service";
  name: string;
  price: number | null;
}

export interface DashboardRead {
  business_name: string;
  business_completeness: number;
  next_action: NextAction;
  counters: ContentCounters;
  calendar: CalendarCoverage;
  today: ContentSummary[];
  upcoming: ContentSummary[];
  in_review: ContentSummary[];
  recent: ContentSummary[];
  top_ideas: ContentIdeaRead[];
  active_jobs: number;
  quick_create?: QuickCreateItem[];
}

export interface QuestionOption {
  value: string;
  label: string;
}

export interface CreationQuestion {
  key: string;
  question: string;
  kind: "choice" | "text" | "money" | "skip_only";
  options: QuestionOption[];
  optional: boolean;
  persist_to: string | null;
}

export interface CalendarDay {
  day: string;
  contents: ContentSummary[];
}

export interface CalendarRead {
  start: string;
  end: string;
  days: CalendarDay[];
  unscheduled: ContentSummary[];
}

export type CampaignDestination = "INSTAGRAM" | "TIKTOK" | "TIKTOK_SHOP";
export type CampaignOutput = "IMAGE" | "VIDEO" | "COPY";
export type CampaignStatus =
  | "DRAFT"
  | "GENERATING"
  | "REVIEW"
  | "APPROVED"
  | "FAILED"
  | "ARCHIVED";

export interface CampaignRead {
  id: string;
  business_id: string;
  product_id: string;
  model_asset_id?: string | null;
  job_id: string | null;
  destination: CampaignDestination;
  outputs_requested: CampaignOutput[];
  failed_outputs: CampaignOutput[];
  status: CampaignStatus;
  title: string;
  brief: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  product: ProductRead | null;
  model?: AssetRead | null;
  contents: ContentRead[];
  allowed_transitions: CampaignStatus[];
}

export interface CampaignSummary {
  id: string;
  title: string;
  destination: CampaignDestination;
  outputs_requested: CampaignOutput[];
  failed_outputs: CampaignOutput[];
  status: CampaignStatus;
  product_id: string;
  product_name: string | null;
  job_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignGenerateAccepted {
  job_id: string;
  campaign_id: string;
  status: JobStatus;
  kind: JobKind;
}

export interface DestinationRead {
  destination: CampaignDestination;
  label: string;
  default_outputs: CampaignOutput[];
  description: string;
}
