'use client';

/* eslint-disable react/no-unescaped-entities */
import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { usePostById } from '@/hooks/use-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';
import { TwitterEmbed } from '@/components/twitter-embed';
import { ClassificationChips } from '@/components/classification-chips';
import { ClassificationAdmin } from '@/components/classification-admin';

export default function PostDetailPage() {
  const params = useParams();
  const postUid = decodeURIComponent(params.post_uid as string);
  
  // State for collapsible debug section
  const [showRawData, setShowRawData] = useState(false);
  
  // Fetch the current post
  const { data: post, isLoading: postLoading, error: postError } = usePostById(postUid);
  
  
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
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Post Not Found</h1>
            <p className="text-gray-600 mb-4">The post you're looking for doesn't exist or couldn't be loaded.</p>
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
              href="/posts"
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
                {post.author_handle ? `@${post.author_handle}` : 'Anonymous User'}
              </h1>
              <div className="flex items-center gap-3 text-sm text-gray-600 mt-1 md:mt-0">
                <span className="font-medium">{post.platform.toUpperCase()}</span>
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
                    <Badge variant={
                      post.submission_status === 'accepted' ? 'default' : 'outline'
                    }>
                      {post.submission_status === 'accepted' ? 'Accepted Note' : 'Submitted Note'}
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

          {/* Twitter Embed with Reply/Quote Chain and Fact Check Status */}
          {(() => {
            // Extract referenced tweets
            const rawJson = post.raw_json as any;
            const referencedTweets = rawJson?.post?.referenced_tweets || [];
            const replyToTweet = referencedTweets.find((ref: any) => ref.type === 'replied_to');
            const quotedTweet = referencedTweets.find((ref: any) => ref.type === 'quoted');
            
            // Find referenced tweets in includes
            let parentTweet = null;
            let quotedTweetData = null;
            
            if (rawJson?.includes?.tweets) {
              if (replyToTweet) {
                parentTweet = rawJson.includes.tweets.find((tweet: any) => tweet.id === replyToTweet.id);
              }
              if (quotedTweet) {
                quotedTweetData = rawJson.includes.tweets.find((tweet: any) => tweet.id === quotedTweet.id);
              }
            }

            const hasTweetChain = parentTweet || quotedTweetData;

            // Single tweet: show side by side with fact check
            if (!hasTweetChain) {
              return (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Tweet Card */}
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle>Tweet - Eligible for Note</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="border-l-4 border-l-blue-500 bg-blue-50/30 rounded-lg p-3">
                        <TwitterEmbed 
                          postId={post.platform_post_id}
                          author={post.author_handle || undefined}
                        />
                      </div>
                    </CardContent>
                  </Card>

                  {/* Fact Check Status Card - Same height */}
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle>Fact Check Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {post.has_note && post.full_body && post.concise_body ? (
                        <div className="space-y-4">
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                            <p className="text-amber-900 text-sm font-medium mb-2">
                              Community Note Submitted
                            </p>
                            <p className="text-gray-900 text-sm">
                              {post.concise_body}
                            </p>
                          </div>
                          {post.citations && post.citations.length > 0 && (
                            <div>
                              <h4 className="font-medium text-sm text-gray-700 mb-2">Citations</h4>
                              <div className="space-y-1">
                                {post.citations.map((citation: any, index: number) => (
                                  <div key={index} className="text-xs text-gray-600">
                                    {typeof citation === 'string' ? citation : JSON.stringify(citation)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-lg p-8 text-center h-full flex flex-col items-center justify-center">
                          <p className="text-gray-600 mb-2">No community note available yet</p>
                          <p className="text-sm text-gray-500">
                            This post is awaiting classification and fact-checking by our AI system.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              );
            }

            // Tweet chain: show normally with fact check below
            return (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>
                      {parentTweet ? "Reply Chain" : quotedTweetData ? "Quote Tweet - Eligible for Note" : "Tweet - Eligible for Note"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col md:flex-row gap-4">
                      {/* Parent Tweet (if this is a reply) */}
                      {parentTweet && (
                        <div className="flex-1">
                          <div className="mb-2 text-sm font-medium text-gray-700 flex items-center">
                            <span>Replying to</span>
                          </div>
                          <div className="border-l-4 border-l-gray-300 bg-gray-50/30 rounded-lg p-3">
                            <TwitterEmbed 
                              postId={parentTweet.id}
                              author={parentTweet.author_id}
                            />
                          </div>
                        </div>
                      )}

                      {/* Main Tweet - Always the note-eligible post */}
                      <div className="flex-1">
                        {parentTweet && (
                          <div className="mb-2 text-sm font-medium text-blue-700 flex items-center">
                            <span>Reply - Eligible for Note</span>
                          </div>
                        )}
                        <div className="border-l-4 border-l-blue-500 bg-blue-50/30 rounded-lg p-3">
                          <TwitterEmbed 
                            postId={post.platform_post_id}
                            author={post.author_handle || undefined}
                          />
                        </div>
                      </div>

                      {/* Quoted Tweet (if this is a quote tweet) */}
                      {quotedTweetData && (
                        <div className="flex-1">
                          <div className="mb-2 text-sm font-medium text-green-700 flex items-center">
                            <span>Quoted Tweet</span>
                          </div>
                          <div className="border-l-4 border-l-green-500 bg-green-50/30 rounded-lg p-3">
                            <TwitterEmbed 
                              postId={quotedTweetData.id}
                              author={quotedTweetData.author_id}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Fact Check Status for tweet chains */}
                <Card>
                  <CardHeader>
                    <CardTitle>Fact Check Status</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {post.has_note && post.full_body && post.concise_body ? (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <p className="text-amber-900 text-sm font-medium mb-2">
                          Community Note Submitted
                        </p>
                        <p className="text-gray-900">
                          {post.concise_body}
                        </p>
                      </div>
                    ) : (
                      <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
                        <p className="text-gray-600 mb-2">No community note available yet</p>
                        <p className="text-sm text-gray-500">
                          This post is awaiting classification and fact-checking by our AI system.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            );
          })()}


          {/* Full Fact Check Details (if note exists) */}
          {post.has_note && post.full_body && (
            <Card>
              <CardHeader>
                <CardTitle>Full Fact Check</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none">
                  <div className="whitespace-pre-wrap text-gray-900">
                    {post.full_body}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Admin Classification Control */}
          <ClassificationAdmin 
            postUid={postUid} 
            onClassified={() => {
              // The mutation in ClassificationAdmin already invalidates the query
              // This is just for any additional actions we might want
            }}
          />

          {/* Debug Section - Raw JSON Data - At the very bottom */}
          <Card className="mt-8 border-dashed">
            <CardHeader>
              <CardTitle 
                className="flex items-center justify-between cursor-pointer hover:text-gray-600"
                onClick={() => setShowRawData(!showRawData)}
              >
                <span className="text-sm font-medium text-gray-700">Debug: Raw X.com JSON Data</span>
                {showRawData ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </CardTitle>
            </CardHeader>
            {showRawData && (
              <CardContent>
                <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
                  <pre className="text-green-400 text-xs font-mono whitespace-pre-wrap">
                    {post.raw_json ? 
                      JSON.stringify(post.raw_json, null, 2) :
                      'No raw JSON data available'
                    }
                  </pre>
                </div>
                <div className="mt-3 text-xs text-gray-500 space-y-1">
                  <p><strong>Post UID:</strong> {post.post_uid}</p>
                  <p><strong>Platform:</strong> {post.platform}</p>
                  <p><strong>Platform Post ID:</strong> {post.platform_post_id}</p>
                  <p><strong>Ingested:</strong> {new Date(post.ingested_at).toLocaleString()}</p>
                  {post.created_at && (
                    <p><strong>Created:</strong> {new Date(post.created_at).toLocaleString()}</p>
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