// API Response Types based on backend schemas


export interface Post {
  post_uid: string;
  platform: string;
  platform_post_id: string;
  author_handle: string | null;
  text: string;
  raw_json: any;
  created_at: string | null;
  ingested_at: string;
  last_error: string | null;
  classified_at: string | null;
}

export interface Topic {
  topic_id: string;
  slug: string;
  display_name: string;
  config: any;
  status: 'active' | 'archived';
  created_at: string;
}

export interface Submission {
  submission_id: string;
  post_uid: string;
  x_note_id: string | null;
  submission_status: 'submitted' | 'accepted' | 'rejected' | 'unknown';
  submitted_by: string | null;
  submitted_at: string;
  response_json: any;
}


export interface IngestResponse {
  added: number;
  skipped: number;
  total_processed: number;
}

// Classification types
export interface ClassificationData {
  type: 'single' | 'multi' | 'hierarchical';
  value?: string;
  values?: Array<{value: string; confidence?: number; reason?: string}>;
  levels?: Array<{level: number; value: string; confidence?: number; reason?: string}>;
  confidence?: number;
  reason?: string;  // Optional reason field for single classifications
}

export interface Classification {
  classifier_slug: string;
  classifier_display_name: string;
  classifier_group: string | null;
  classification_type: string;
  classification_data: ClassificationData;
  output_schema: any;
  created_at: string;
  updated_at: string;
}

export interface Classifier {
  classifier_id: string;
  slug: string;
  display_name: string;
  description: string | null;
  group_name: string | null;
  is_active: boolean;
  output_schema: any;
  config: any;
  created_at: string;
  updated_at: string;
  classification_count?: number;
}

// New post types for browsing
export interface PostPublic {
  post_uid: string;
  platform: string;
  platform_post_id: string;
  author_handle: string | null;
  text: string;
  created_at: string | null;
  ingested_at: string;
  has_note: boolean;
  has_fact_check: boolean;
  submission_status: string | null;
  topic_slug: string | null;
  topic_display_name: string | null;
  generated_at: string | null;
  // Raw JSON data (for debugging)
  raw_json?: any;
  // Classifications
  classifications?: Classification[];
}

export interface PostListResponse {
  posts: PostPublic[];
  total: number;
  limit: number;
  offset: number;
}