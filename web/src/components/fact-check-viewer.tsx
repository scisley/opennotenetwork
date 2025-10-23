"use client";

import { useState, useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import {
  useFactChecks,
  useRunFactCheck,
  useFactCheckers,
} from "@/hooks/use-api";
import { FactCheckDisplayPublic } from "@/components/fact-check-display-public";

interface FactCheckViewerProps {
  postUid: string;
  onFactCheckChange?: (factCheckId: string | null | undefined) => void;
}

export function FactCheckViewer({ postUid, onFactCheckChange }: FactCheckViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const { user } = useUser();

  // Check if user is admin
  const isAdmin = user?.publicMetadata?.role === "admin";

  const { data: factChecksData, isLoading: checksLoading } =
    useFactChecks(postUid);
  const { data: factCheckersData } = useFactCheckers();
  const runFactCheck = useRunFactCheck(postUid);

  const factChecks = factChecksData?.fact_checks || [];
  const factCheckers = factCheckersData?.fact_checkers || [];

  // Get current fact check
  const currentCheck = factChecks[currentIndex];

  // Notify parent when fact check changes
  useEffect(() => {
    if (onFactCheckChange) {
      // undefined = still loading, null = no fact check, string = fact check ID
      if (checksLoading) {
        onFactCheckChange(undefined);
      } else {
        const factCheckId = currentCheck?.id || currentCheck?.fact_check_id || null;
        onFactCheckChange(factCheckId);
      }
    }
  }, [currentCheck, checksLoading, onFactCheckChange]);

  // Handle navigation
  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : factChecks.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < factChecks.length - 1 ? prev + 1 : 0));
  };


  // Handle running fact checkers that haven't been run yet
  const handleRunNewChecker = async (slug: string) => {
    await runFactCheck.mutateAsync({ factCheckerSlug: slug, force: false });
  };

  // Find fact checkers that haven't been run yet
  const availableCheckers = factCheckers.filter(
    (checker: any) =>
      !factChecks.some((check: any) => check.fact_checker.slug === checker.slug)
  );

  if (checksLoading) {
    return (
      <Card className="border-0 shadow-none">
        <CardContent className="p-0">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div>
      {factChecks.length > 1 && (
        <div className="flex items-center justify-end mb-4">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={goToPrevious}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-gray-600 min-w-[60px] text-center">
              {`${currentIndex + 1} / ${factChecks.length}`}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={goToNext}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
      <div>
        {currentCheck ? (
          /* Use the shared public display component */
          <FactCheckDisplayPublic factCheck={currentCheck} />
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-600 mb-4">
              No fact checks have been run yet.
            </p>
            {isAdmin && availableCheckers.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-gray-500 mb-3">
                  Available fact checkers:
                </p>
                {availableCheckers.map((checker: any) => (
                  <div
                    key={checker.slug}
                    className="flex items-center justify-between max-w-md mx-auto"
                  >
                    <div className="text-left">
                      <p className="font-medium text-sm">{checker.name}</p>
                      <p className="text-xs text-gray-500">
                        {checker.description}
                      </p>
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
                {factCheckers.length} fact checker
                {factCheckers.length !== 1 ? "s" : ""} available
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
