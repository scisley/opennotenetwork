'use client';

import { useParams, notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { usePostById } from '@/hooks/use-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PostClassifications } from '@/components/post-classifications';
import { RawJsonViewer } from '@/components/raw-json-viewer';

export default function PostManagePage() {
  const params = useParams();
  const postUid = params.post_uid as string;
  const { data: post, isLoading, error } = usePostById(postUid);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <p>Loading post...</p>
        </div>
      </div>
    );
  }

  if (error || !post) {
    notFound();
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Back to post button */}
        <div className="flex items-center justify-between">
          <Link href={`/posts/${postUid}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Post
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">Manage Post</h1>
        </div>

        {/* Post Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>Post Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Post ID</p>
                <p className="font-mono text-sm">{post.post_uid}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Platform</p>
                <p className="text-sm capitalize">{post.platform}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Author</p>
                <p className="text-sm">@{post.author_handle || 'unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created</p>
                <p className="text-sm">{post.created_at ? new Date(post.created_at).toLocaleDateString() : new Date(post.ingested_at).toLocaleDateString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Classifications Management */}
        <PostClassifications postUid={postUid} />

        {/* Raw JSON Data */}
        <RawJsonViewer data={post.raw_json} title="Raw X.com JSON" />
      </div>
    </div>
  );
}