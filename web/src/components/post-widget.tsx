"use client";

/**
 * PostWidget Component
 *
 * Displays posts in a Twitter/X-style card format with media support.
 *
 * Note: This component intentionally uses <img> tags instead of Next.js <Image />
 * because the media URLs are from external Twitter/X CDN sources that:
 * - Cannot be optimized by Next.js
 * - May change or expire
 * - Are not under our control
 *
 * ESLint warnings for @next/next/no-img-element are intentionally disabled.
 */

import Link from "next/link";
import { PostPublic } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Play, MessageCircle, Heart, Repeat, ChartBar } from "lucide-react";

import {
  extractMediaFromPost,
  extractAuthorInfo,
  formatRelativeTime,
  extractEngagementMetrics,
  MediaItem,
} from "@/lib/post-utils";
import { cn } from "@/lib/utils";

interface PostWidgetProps {
  post: PostPublic;
  href: string;
  className?: string;
}

function MediaGrid({ media }: { media: MediaItem[] }) {
  if (media.length === 0) return null;

  const displayMedia = media.slice(0, 4); // Max 4 images

  if (displayMedia.length === 1) {
    const item = displayMedia[0];
    return (
      <div className="relative w-full h-48 bg-gray-100 rounded-lg overflow-hidden">
        {item.type === "video" ? (
          <>
            {item.preview_image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.preview_image_url}
                alt="Video thumbnail"
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-black bg-opacity-60 rounded-full p-3">
                <Play className="w-6 h-6 text-white fill-white" />
              </div>
            </div>
          </>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.url}
            alt="Post media"
            className="w-full h-full object-cover"
          />
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "grid gap-0.5 rounded-lg overflow-hidden h-48",
        displayMedia.length === 2 && "grid-cols-2",
        displayMedia.length === 3 && "grid-cols-2",
        displayMedia.length === 4 && "grid-cols-2 grid-rows-2"
      )}
    >
      {displayMedia.map((item, index) => (
        <div
          key={index}
          className={cn(
            "relative bg-gray-100",
            displayMedia.length === 3 && index === 0 && "row-span-2"
          )}
        >
          {item.type === "video" ? (
            <>
              {item.preview_image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={item.preview_image_url}
                  alt="Video thumbnail"
                  className="w-full h-full object-cover"
                />
              )}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="bg-black bg-opacity-60 rounded-full p-2">
                  <Play className="w-4 h-4 text-white fill-white" />
                </div>
              </div>
            </>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.url}
              alt="Post media"
              className="w-full h-full object-cover"
            />
          )}
        </div>
      ))}
    </div>
  );
}

function EngagementMetrics({ post }: { post: PostPublic }) {
  const metrics = extractEngagementMetrics(post);

  if (!metrics.replies && !metrics.reposts && !metrics.likes && !metrics.views) {
    return null;
  }

  const formatCount = (count?: number) => {
    if (!count) return "0";
    if (count >= 1000000) {
      return (count / 1000000).toFixed(1) + "M";
    }
    if (count >= 1000) {
      return (count / 1000).toFixed(1) + "K";
    }
    return count.toString();
  };

  return (
    <div className="flex items-center gap-4 text-gray-500 text-sm">
      {metrics.replies !== undefined && (
        <div className="flex items-center gap-1">
          <MessageCircle className="w-4 h-4" />
          <span>{formatCount(metrics.replies)}</span>
        </div>
      )}
      {metrics.reposts !== undefined && (
        <div className="flex items-center gap-1">
          <Repeat className="w-4 h-4" />
          <span>{formatCount(metrics.reposts)}</span>
        </div>
      )}
      {metrics.likes !== undefined && (
        <div className="flex items-center gap-1">
          <Heart className="w-4 h-4" />
          <span>{formatCount(metrics.likes)}</span>
        </div>
      )}
      {metrics.views !== undefined && (
        <div className="flex items-center gap-1">
          <ChartBar className="w-4 h-4" />
          <span>{formatCount(metrics.views)}</span>
        </div>
      )}
    </div>
  );
}

export function PostWidget({ post, href, className }: PostWidgetProps) {
  const media = extractMediaFromPost(post);
  const author = extractAuthorInfo(post);
  const relativeTime = formatRelativeTime(post.created_at || post.ingested_at);

  return (
    <Link
      href={href}
      className={cn(
        "bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all cursor-pointer overflow-hidden h-[450px] flex flex-col relative group",
        className
      )}
    >
      {/* X Logo in top right corner */}
      <div className="absolute top-3 right-3 z-10">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/x-logo-small.png"
          alt="X"
          className="w-6 h-6 opacity-60"
        />
      </div>

      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-sm truncate">
              {author?.name || author?.username || "Unknown"}
            </span>
            {author?.verified && (
              <svg className="w-4 h-4 text-blue-500" viewBox="0 0 22 22" fill="currentColor">
                <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"/>
              </svg>
            )}
          </div>
          <span className="text-sm text-gray-500 truncate block">
            @{author?.username || post.author_handle || "unknown"} · {relativeTime}
          </span>
        </div>
      </div>

      {/* Content - with overflow handling */}
      <div className="flex-1 overflow-hidden relative px-4">
        <div className="space-y-3">
          {/* Text */}
          <p className="text-gray-900 text-sm leading-relaxed">
            {post.text}
          </p>

          {/* Media */}
          {media.length > 0 && <MediaGrid media={media} />}
        </div>

        {/* Gradient overlay for overflow content */}
        <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-white via-white/95 to-transparent pointer-events-none" />
      </div>

      {/* Footer - always visible */}
      <div className="px-4 pb-4 pt-2 space-y-3 bg-white relative z-10">
        {/* Engagement Metrics */}
        <EngagementMetrics post={post} />

        {/* Status badges */}
        <div className="flex items-center gap-2">
          {post.has_fact_check && !post.has_note && (
            <span className="text-xs text-gray-500">
              Has fact-check
            </span>
          )}
          {post.has_note && post.submission_status === "displayed" && (
            <Badge variant="default" className="text-xs bg-green-600 hover:bg-green-700">
              Rated Helpful
            </Badge>
          )}
          {post.has_note && post.submission_status === "not_displayed" && (
            <Badge variant="default" className="text-xs bg-red-600 hover:bg-red-700">
              Rated Unhelpful
            </Badge>
          )}
          {post.has_note && post.submission_status === "submitted" && (
            <Badge variant="secondary" className="text-xs">
              Needs more ratings
            </Badge>
          )}
          {post.has_note && !post.submission_status && (
            <span className="text-xs text-gray-500">
              Note written
            </span>
          )}
          {post.has_note && post.submission_status && !["displayed", "not_displayed", "submitted"].includes(post.submission_status) && (
            <span className="text-xs text-gray-500">
              Note submitted
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}