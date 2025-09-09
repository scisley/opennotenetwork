"use client";

/* eslint-disable react/no-unescaped-entities */
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { usePostById } from "@/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Settings } from "lucide-react";
import { TwitterEmbed } from "@/components/twitter-embed";
import { ClassificationChips } from "@/components/classification-chips";
import { FactCheckViewer } from "@/components/fact-check-viewer";
import { NoteViewer } from "@/components/note-viewer";

export default function PostDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const postUid = decodeURIComponent(params.post_uid as string);
  const { user } = useUser();

  // Check if user is admin
  const isAdmin = user?.publicMetadata?.role === "admin";

  
  // Build the back link with preserved query parameters from the current URL
  const backToPostsUrl = searchParams.toString() 
    ? `/posts?${searchParams.toString()}`
    : "/posts";

  // Fetch the current post
  const {
    data: post,
    isLoading: postLoading,
    error: postError,
  } = usePostById(postUid);

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
      {/* Navigation Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link
              href={backToPostsUrl}
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Posts
            </Link>
            {isAdmin && (
              <Link
                href={`/posts/${postUid}/manage`}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
                title="Manage Post"
              >
                <Settings className="w-5 h-5" />
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Post Header */}
          <div className="flex items-start justify-between">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between w-full">
              <h1 className="text-2xl font-bold text-gray-900">
                {post.author_handle
                  ? `@${post.author_handle}`
                  : "Anonymous User"}
              </h1>
              <div className="flex items-center gap-3 text-sm text-gray-600 mt-1 md:mt-0">
                <span className="font-medium">
                  {post.platform.toUpperCase()}
                </span>
                <span>•</span>
                <span>
                  {post.created_at
                    ? new Date(post.created_at).toLocaleString()
                    : new Date(post.ingested_at).toLocaleString()}
                </span>
                {post.topic_display_name && (
                  <>
                    <span>•</span>
                    <Badge variant="secondary">{post.topic_display_name}</Badge>
                  </>
                )}
                {post.has_note && (
                  <>
                    <span>•</span>
                    <Badge
                      variant={
                        post.submission_status === "accepted"
                          ? "default"
                          : "outline"
                      }
                    >
                      {post.submission_status === "accepted"
                        ? "Accepted Note"
                        : "Submitted Note"}
                    </Badge>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Classifications - Minimal chips above tweet */}
          {post.classifications && post.classifications.length > 0 && (
            <ClassificationChips classifications={post.classifications} />
          )}

          {/* Twitter Embed and Note - Side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Tweet Card */}
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Tweet - Eligible for Note</CardTitle>
              </CardHeader>
              <CardContent>
                <TwitterEmbed
                  postId={post.platform_post_id}
                  author={post.author_handle || undefined}
                />
              </CardContent>
            </Card>

            {/* Note Viewer - Same height */}
            <div className="h-full">
              <NoteViewer 
                conciseBody={post.concise_body}
                submissionStatus={post.submission_status}
                hasNote={post.has_note}
              />
            </div>
          </div>

          {/* Fact Check Viewer - Full width below */}
          <div className="w-full">
            <FactCheckViewer postUid={postUid} />
          </div>


        </div>
      </div>
    </div>
  );
}
