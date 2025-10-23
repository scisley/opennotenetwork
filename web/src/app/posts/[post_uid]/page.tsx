"use client";

/* eslint-disable react/no-unescaped-entities */
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { usePostById } from "@/hooks/use-api";
import { Settings } from "lucide-react";
import { TwitterEmbed } from "@/components/twitter-embed";
import { FactCheckViewer } from "@/components/fact-check-viewer";
import { CommunityNote } from "@/components/community-note";
import { PostDetails } from "@/components/post-details";
import { SiteHeader } from "@/components/site-header";
import { useAnalytics } from "@/hooks/use-analytics";

export default function PostDetailPage() {
  const params = useParams();
  const postUid = decodeURIComponent(params.post_uid as string);
  const { user } = useUser();
  const { trackPostViewed } = useAnalytics();
  const [currentFactCheckId, setCurrentFactCheckId] = useState<string | null | undefined>(undefined);

  // Check if user is admin
  const isAdmin = user?.publicMetadata?.role === "admin";

  // Fetch the current post
  const {
    data: post,
    isLoading: postLoading,
    error: postError,
  } = usePostById(postUid);

  // Track post view when post data loads
  useEffect(() => {
    if (post && !postLoading) {
      trackPostViewed({
        post_uid: post.post_uid,
        has_fact_check: post.has_fact_check || false,
        has_note: post.has_note || false,
        has_submitted_note: post.submission_status === "submitted" || post.submission_status === "accepted",
      });
    }
  }, [post, postLoading, trackPostViewed]);

  if (postLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (postError || !post) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Post Not Found
            </h1>
            <p className="text-gray-600 mb-4">
              The post you're looking for doesn't exist or couldn't be loaded.
            </p>
            <Link href="/posts" className="text-blue-600 hover:text-blue-800">
              ← Back to Posts
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Admin manage link */}
        {isAdmin && (
          <div className="flex justify-end mb-4">
            <Link
              href={`/posts/${postUid}/manage`}
              className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors"
              title="Manage Post"
            >
              <Settings className="w-4 h-4 mr-1" />
              Manage Post
            </Link>
          </div>
        )}

        <div className="space-y-6">
          {/* Twitter Embed and Note - Side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
            {/* Tweet - no wrapper, let embed handle its own styling */}
            <TwitterEmbed
              postId={post.platform_post_id}
              author={post.author_handle || undefined}
            />

            {/* Community Note Card */}
            <CommunityNote
              factCheckId={currentFactCheckId}
              submissionStatus={post.submission_status}
            />
          </div>

          {/* Fact Check Viewer - Full width below */}
          <div className="w-full">
            <FactCheckViewer
              postUid={postUid}
              onFactCheckChange={setCurrentFactCheckId}
            />
          </div>

          {/* Post Details - Classifications with icons */}
          {post.classifications && post.classifications.length > 0 && (
            <PostDetails classifications={post.classifications} />
          )}

        </div>
      </div>
    </div>
  );
}
