import { PostPublic } from "@/types/api";

export interface MediaItem {
  type: "photo" | "video";
  url: string;
  width?: number;
  height?: number;
  media_key?: string;
  preview_image_url?: string; // For videos
}

export interface AuthorInfo {
  username: string;
  name?: string;
  verified?: boolean;
  profile_image_url?: string;
}

/**
 * Extract media items from a post's raw JSON
 */
export function extractMediaFromPost(post: PostPublic): MediaItem[] {
  if (!post.raw_json?.includes?.media) {
    return [];
  }

  const media = post.raw_json.includes.media;
  if (!Array.isArray(media)) {
    return [];
  }

  return media.map((item: any) => {
    // Twitter/X media objects have the URL in different fields depending on type
    let url = "";
    if (item.type === "photo") {
      url = item.url || "";
    } else if (item.type === "video") {
      url = item.preview_image_url || "";
    }

    return {
      type: item.type || "photo",
      url: url,
      width: item.width,
      height: item.height,
      media_key: item.media_key,
      preview_image_url: item.preview_image_url,
    };
  }).filter((item: MediaItem) => item.url);
}

/**
 * Extract author information from a post's raw JSON
 */
export function extractAuthorInfo(post: PostPublic): AuthorInfo | null {
  // First try to get from includes.users
  if (post.raw_json?.includes?.users?.[0]) {
    const user = post.raw_json.includes.users[0];
    return {
      username: user.username || post.author_handle || "unknown",
      name: user.name,
      verified: user.verified || false,
      profile_image_url: user.profile_image_url,
    };
  }

  // Fallback to basic info
  if (post.author_handle) {
    return {
      username: post.author_handle,
    };
  }

  return null;
}

/**
 * Format a timestamp as relative time (e.g., "2h ago", "3d ago")
 */
export function formatRelativeTime(timestamp: string | null): string {
  if (!timestamp) return "";

  const date = new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) {
    return "just now";
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h`;
  }

  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days}d`;
  }

  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months}mo`;
  }

  const years = Math.floor(months / 12);
  return `${years}y`;
}

/**
 * Get engagement metrics from a post's raw JSON
 */
export function extractEngagementMetrics(post: PostPublic): {
  likes?: number;
  reposts?: number;
  replies?: number;
  views?: number;
} {
  const metrics = post.raw_json?.post?.public_metrics;
  if (!metrics) return {};

  return {
    likes: metrics.like_count,
    reposts: metrics.retweet_count,
    replies: metrics.reply_count,
    views: metrics.impression_count,
  };
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + "...";
}