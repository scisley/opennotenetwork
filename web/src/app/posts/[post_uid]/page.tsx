"use client";

/* eslint-disable react/no-unescaped-entities */
import { useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { usePostById } from "@/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ChevronDown, ChevronUp } from "lucide-react";
import { TwitterEmbed } from "@/components/twitter-embed";
import { ClassificationChips } from "@/components/classification-chips";
import { ClassificationAdmin } from "@/components/classification-admin";
import { FactCheckViewer } from "@/components/fact-check-viewer";

export default function PostDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const postUid = decodeURIComponent(params.post_uid as string);
  const { user } = useUser();

  // Check if user is admin
  const isAdmin = user?.publicMetadata?.role === "admin";

  // State for collapsible debug section
  const [showRawData, setShowRawData] = useState(false);
  
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

          {/* Twitter Embed and Fact Check */}
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

            {/* Fact Check Viewer - Same height */}
            <div className="h-full">
              <FactCheckViewer postUid={postUid} />
            </div>
          </div>

          {/* Community Note Status (if exists) */}
          {post.has_note && post.concise_body && (
            <Card>
              <CardHeader>
                <CardTitle>Community Note Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-amber-900 text-sm font-medium">
                        Community Note{" "}
                        {post.submission_status === "accepted"
                          ? "Accepted"
                          : "Submitted"}
                      </p>
                      <Badge
                        variant={
                          post.submission_status === "accepted"
                            ? "default"
                            : "secondary"
                        }
                      >
                        {post.submission_status || "Submitted"}
                      </Badge>
                    </div>
                    <p className="text-gray-900 text-sm mb-3">
                      {post.concise_body}
                    </p>
                    {post.full_body && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm text-amber-700 hover:text-amber-800">
                          View full fact check
                        </summary>
                        <div className="mt-3 pt-3 border-t border-amber-200">
                          <div className="whitespace-pre-wrap text-gray-700 text-sm">
                            {post.full_body}
                          </div>
                        </div>
                      </details>
                    )}
                  </div>
                  {post.citations && post.citations.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm text-gray-700 mb-2">
                        Citations
                      </h4>
                      <div className="space-y-1">
                        {post.citations.map((citation: any, index: number) => (
                          <div key={index} className="text-xs text-gray-600">
                            {typeof citation === "string"
                              ? citation
                              : JSON.stringify(citation)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Admin Classification Control - Only show for admin users */}
          {isAdmin && (
            <ClassificationAdmin
              postUid={postUid}
              onClassified={() => {
                // The mutation in ClassificationAdmin already invalidates the query
                // This is just for any additional actions we might want
              }}
            />
          )}

          {/* Debug Section - Raw JSON Data - At the very bottom */}
          <Card className="mt-8 border-dashed">
            <CardHeader>
              <CardTitle
                className="flex items-center justify-between cursor-pointer hover:text-gray-600"
                onClick={() => setShowRawData(!showRawData)}
              >
                <span className="text-sm font-medium text-gray-700">
                  Debug: Raw X.com JSON Data
                </span>
                {showRawData ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </CardTitle>
            </CardHeader>
            {showRawData && (
              <CardContent>
                <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-[48rem]">
                  <pre className="text-green-400 text-xs font-mono whitespace-pre-wrap">
                    {post.raw_json
                      ? JSON.stringify(post.raw_json, null, 2)
                      : "No raw JSON data available"}
                  </pre>
                </div>
                <div className="mt-3 text-xs text-gray-500 space-y-1">
                  <p>
                    <strong>Post UID:</strong> {post.post_uid}
                  </p>
                  <p>
                    <strong>Platform:</strong> {post.platform}
                  </p>
                  <p>
                    <strong>Platform Post ID:</strong> {post.platform_post_id}
                  </p>
                  <p>
                    <strong>Ingested:</strong>{" "}
                    {new Date(post.ingested_at).toLocaleString()}
                  </p>
                  {post.created_at && (
                    <p>
                      <strong>Created:</strong>{" "}
                      {new Date(post.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
