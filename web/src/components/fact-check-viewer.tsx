'use client';

import { useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronLeft, ChevronRight, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { useFactChecks, useRunFactCheck, useDeleteFactCheck, useFactCheckers } from '@/hooks/use-api';
import ReactMarkdown from 'react-markdown';

interface FactCheckViewerProps {
  postUid: string;
}

export function FactCheckViewer({ postUid }: FactCheckViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const { user } = useUser();
  
  // Check if user is admin
  const isAdmin = user?.publicMetadata?.role === 'admin';
  
  const { data: factChecksData, isLoading: checksLoading } = useFactChecks(postUid);
  const { data: factCheckersData } = useFactCheckers();
  const runFactCheck = useRunFactCheck(postUid);
  const deleteFactCheck = useDeleteFactCheck(postUid);
  
  const factChecks = factChecksData?.fact_checks || [];
  const factCheckers = factCheckersData?.fact_checkers || [];
  
  // Get current fact check
  const currentCheck = factChecks[currentIndex];
  
  // Handle navigation
  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : factChecks.length - 1));
  };
  
  const goToNext = () => {
    setCurrentIndex((prev) => (prev < factChecks.length - 1 ? prev + 1 : 0));
  };
  
  // Handle rerun
  const handleRerun = async () => {
    if (currentCheck) {
      // Delete current check first
      await deleteFactCheck.mutateAsync(currentCheck.fact_checker.slug);
      // Then run it again
      await runFactCheck.mutateAsync({ 
        factCheckerSlug: currentCheck.fact_checker.slug, 
        force: true 
      });
    }
  };
  
  // Handle running fact checkers that haven't been run yet
  const handleRunNewChecker = async (slug: string) => {
    await runFactCheck.mutateAsync({ factCheckerSlug: slug, force: false });
  };
  
  // Find fact checkers that haven't been run yet
  const availableCheckers = factCheckers.filter(
    (checker: any) => !factChecks.some((check: any) => check.fact_checker.slug === checker.slug)
  );
  
  if (checksLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fact Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Fact Checks</CardTitle>
          {factChecks.length > 0 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={goToPrevious}
                disabled={factChecks.length <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-gray-600 min-w-[60px] text-center">
                {factChecks.length > 0 ? `${currentIndex + 1} / ${factChecks.length}` : '0 / 0'}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={goToNext}
                disabled={factChecks.length <= 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {currentCheck ? (
          <div className="space-y-4">
            {/* Fact Checker Info */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{currentCheck.fact_checker.name}</h3>
                <Badge variant="outline" className="text-xs">
                  v{currentCheck.fact_checker.version}
                </Badge>
              </div>
              
              {/* Status Badge */}
              <div className="flex items-center gap-2">
                {currentCheck.status === 'completed' && (
                  <Badge variant="default">Completed</Badge>
                )}
                {currentCheck.status === 'processing' && (
                  <Badge variant="secondary" className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Processing
                  </Badge>
                )}
                {currentCheck.status === 'failed' && (
                  <Badge variant="destructive">Failed</Badge>
                )}
                {currentCheck.status === 'pending' && (
                  <Badge variant="outline">Pending</Badge>
                )}
                
                {isAdmin && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRerun}
                    disabled={runFactCheck.isPending || deleteFactCheck.isPending || currentCheck.status === 'processing'}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Rerun
                  </Button>
                )}
              </div>
            </div>
            
            {/* Verdict and Confidence */}
            {currentCheck.verdict && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Verdict:</span>
                  <Badge 
                    variant={
                      currentCheck.verdict === 'true' ? 'default' :
                      currentCheck.verdict === 'false' ? 'destructive' :
                      currentCheck.verdict === 'misleading' ? 'secondary' :
                      'outline'
                    }
                  >
                    {currentCheck.verdict}
                  </Badge>
                </div>
                {currentCheck.confidence !== null && currentCheck.confidence !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Confidence:</span>
                    <span className="text-sm">{(currentCheck.confidence * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            )}
            
            {/* Error Message */}
            {currentCheck.status === 'failed' && currentCheck.error_message && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-900">Error</p>
                    <p className="text-sm text-red-700 mt-1">{currentCheck.error_message}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Fact Check Content */}
            {currentCheck.status === 'completed' && currentCheck.result?.text && (
              <div className="prose prose-sm max-w-none">
                <div className="bg-gray-50 rounded-lg p-4">
                  <ReactMarkdown>{currentCheck.result.text}</ReactMarkdown>
                </div>
              </div>
            )}
            
            {/* Claims if available */}
            {currentCheck.result?.claims && currentCheck.result.claims.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Individual Claims</h4>
                {currentCheck.result.claims.map((claim: any, idx: number) => (
                  <div key={idx} className="bg-gray-50 rounded p-3 text-sm">
                    <p className="font-medium mb-1">{claim.claim}</p>
                    {claim.verdict && (
                      <Badge variant="outline" className="text-xs mb-1">
                        {claim.verdict}
                      </Badge>
                    )}
                    {claim.explanation && (
                      <p className="text-gray-600 mt-1">{claim.explanation}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* Sources if available */}
            {currentCheck.result?.sources && currentCheck.result.sources.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Sources</h4>
                {currentCheck.result.sources.map((source: any, idx: number) => (
                  <div key={idx} className="bg-gray-50 rounded p-2 text-sm">
                    <p>{source.description}</p>
                    {source.relevance && (
                      <p className="text-gray-600 text-xs mt-1">{source.relevance}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* Timestamps */}
            <div className="text-xs text-gray-500 pt-2 border-t">
              <p>Created: {new Date(currentCheck.created_at).toLocaleString()}</p>
              {currentCheck.updated_at !== currentCheck.created_at && (
                <p>Updated: {new Date(currentCheck.updated_at).toLocaleString()}</p>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-600 mb-4">No fact checks have been run yet.</p>
            {isAdmin && availableCheckers.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-gray-500 mb-3">Available fact checkers:</p>
                {availableCheckers.map((checker: any) => (
                  <div key={checker.slug} className="flex items-center justify-between max-w-md mx-auto">
                    <div className="text-left">
                      <p className="font-medium text-sm">{checker.name}</p>
                      <p className="text-xs text-gray-500">{checker.description}</p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleRunNewChecker(checker.slug)}
                      disabled={runFactCheck.isPending}
                    >
                      Run
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {!isAdmin && factCheckers.length > 0 && (
              <p className="text-sm text-gray-500">
                {factCheckers.length} fact checker{factCheckers.length !== 1 ? 's' : ''} available
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}