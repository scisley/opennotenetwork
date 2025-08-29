'use client';

import { useEffect } from 'react';
import { useClassifiers, useClassifyPost } from '@/hooks/use-api';
import { useLocalStorage } from '@/hooks/use-local-storage';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Play, CheckCircle, XCircle } from 'lucide-react';

interface ClassificationAdminProps {
  postUid: string;
  onClassified?: () => void;
}

export function ClassificationAdmin({ postUid, onClassified }: ClassificationAdminProps) {
  const { data: classifiersData, isLoading: loadingClassifiers } = useClassifiers();
  const classifyMutation = useClassifyPost(postUid);
  const [selectedClassifiers, setSelectedClassifiers] = useLocalStorage<string[]>('selectedClassifiers', []);
  const [runAll, setRunAll] = useLocalStorage('runAllClassifiers', false);

  const activeClassifiers = classifiersData?.classifiers.filter(c => c.is_active) || [];

  // Clean up invalid classifiers from localStorage
  useEffect(() => {
    if (activeClassifiers.length > 0 && selectedClassifiers.length > 0) {
      const validSlugs = activeClassifiers.map(c => c.slug);
      const validSelected = selectedClassifiers.filter(slug => validSlugs.includes(slug));
      
      if (validSelected.length !== selectedClassifiers.length) {
        setSelectedClassifiers(validSelected);
      }
    }
  }, [activeClassifiers, selectedClassifiers, setSelectedClassifiers]);

  const handleClassify = async () => {
    const slugs = runAll ? undefined : selectedClassifiers.length > 0 ? selectedClassifiers : undefined;
    
    console.log('Classifying with:', { runAll, selectedClassifiers, slugs });
    
    await classifyMutation.mutateAsync({
      classifierSlugs: slugs,
      force: true
    });
    
    if (onClassified) {
      onClassified();
    }
  };

  const toggleClassifier = (slug: string) => {
    setSelectedClassifiers(prev => 
      prev.includes(slug) 
        ? prev.filter(s => s !== slug)
        : [...prev, slug]
    );
    setRunAll(false);
  };

  return (
    <Card className="border-orange-200 bg-orange-50">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Play className="w-4 h-4" />
          Run Classifiers (Admin)
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loadingClassifiers ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading classifiers...
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <Checkbox 
                  checked={runAll}
                  onCheckedChange={(checked) => {
                    setRunAll(!!checked);
                    if (checked) setSelectedClassifiers([]);
                  }}
                />
                <span className="font-medium">Run all active classifiers</span>
              </label>
              
              {!runAll && (
                <div className="ml-6 space-y-1">
                  {activeClassifiers.map(classifier => (
                    <label key={classifier.slug} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedClassifiers.includes(classifier.slug)}
                        onCheckedChange={() => toggleClassifier(classifier.slug)}
                      />
                      <span>{classifier.display_name}</span>
                      {classifier.group_name && (
                        <span className="text-xs text-gray-500">({classifier.group_name})</span>
                      )}
                    </label>
                  ))}
                </div>
              )}
            </div>

            <Button
              onClick={handleClassify}
              disabled={classifyMutation.isPending || (!runAll && selectedClassifiers.length === 0)}
              className="w-full"
            >
              {classifyMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Running Classifiers...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run {runAll ? 'All' : selectedClassifiers.length} Classifier{runAll || selectedClassifiers.length !== 1 ? 's' : ''}
                </>
              )}
            </Button>

            {classifyMutation.isSuccess && (
              <Alert className="border-green-200 bg-green-50">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <AlertDescription>
                  Classification complete! 
                  {classifyMutation.data && (
                    <span className="ml-1">
                      ({classifyMutation.data.classified} classified, {classifyMutation.data.skipped} skipped)
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {classifyMutation.isError && (
              <Alert className="border-red-200 bg-red-50">
                <XCircle className="w-4 h-4 text-red-600" />
                <AlertDescription>
                  Classification failed. Please try again.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}