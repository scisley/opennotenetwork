'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams, notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { usePostById, useFactChecks } from '@/hooks/use-api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PostClassifications } from '@/components/post-classifications';
import { RawJsonViewer } from '@/components/raw-json-viewer';
import { TwitterEmbed } from '@/components/twitter-embed';
import { FactCheckManager } from '@/components/fact-check-manager';
import { FactCheckerSelector } from '@/components/fact-checker-selector';
import { NoteManager } from '@/components/note-manager';

export default function PostManagePage() {
  const params = useParams();
  const postUid = params.post_uid as string;
  const { data: post, isLoading, error } = usePostById(postUid);
  const { data: factChecksData } = useFactChecks(postUid);

  const [selectedChecker, setSelectedChecker] = useState<string | null>(null);

  // Memoize factChecks to avoid re-render issues
  const factChecks = useMemo(
    () => factChecksData?.fact_checks || [],
    [factChecksData]
  );

  // Derive current fact check from selected checker
  const currentFactCheck = useMemo(() => {
    if (!selectedChecker) return null;
    return factChecks.find(
      (fc: any) => fc.fact_checker.slug === selectedChecker
    ) || null;
  }, [selectedChecker, factChecks]);

  // Auto-select first fact checker when fact checks load
  useEffect(() => {
    if (!selectedChecker && factChecks.length > 0) {
      setSelectedChecker(factChecks[0].fact_checker.slug);
    }
  }, [factChecks, selectedChecker]);

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

        {/* Fact Checker Selector */}
        <FactCheckerSelector
          factChecks={factChecks}
          selectedChecker={selectedChecker}
          onCheckerSelect={setSelectedChecker}
        />

        {/* Twitter Embed and Note Management - Side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          {/* Twitter Embed */}
          <Card className="p-4">
            <TwitterEmbed
              postId={post.platform_post_id}
              defaultCollapsed={true}
            />
          </Card>

          {/* Note Management */}
          {currentFactCheck && currentFactCheck.status === "completed" ? (
            <NoteManager
              factCheckId={currentFactCheck.id || currentFactCheck.fact_check_id}
              postUid={postUid}
            />
          ) : (
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Community Note Generation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-gray-600">
                    {currentFactCheck
                      ? "Fact check must be completed before generating notes"
                      : "Select a fact checker above to view notes"}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Fact Check Details */}
        <FactCheckManager
          postUid={postUid}
          selectedChecker={selectedChecker}
        />

        {/* Classifications Management */}
        <PostClassifications postUid={postUid} />

        {/* Raw JSON Data */}
        <RawJsonViewer data={post.raw_json} title="Raw X.com JSON" />
      </div>
    </div>
  );
}