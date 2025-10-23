"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Trash2, Plus, Eye } from "lucide-react";
import Link from "next/link";
import {
  useFactChecks,
  useFactCheckers,
  useDeleteFactCheck,
} from "@/hooks/use-api";
import { FactCheckDisplay } from "./fact-check-display";

interface FactCheckManagerProps {
  postUid: string;
  selectedChecker: string | null;
}

export function FactCheckManager({ postUid, selectedChecker }: FactCheckManagerProps) {
  
  // Fetch data
  const { data: factChecksData, isLoading: checksLoading, refetch: refetchFactChecks } = useFactChecks(postUid);
  const { data: factCheckersData, isLoading: checkersLoading } = useFactCheckers();
  const deleteFactCheck = useDeleteFactCheck(postUid);
  
  const factChecks = useMemo(
    () => factChecksData?.fact_checks || [],
    [factChecksData]
  );
  const factCheckers = factCheckersData?.fact_checkers || [];
  
  // Get the currently selected fact check
  const selectedFactCheck = selectedChecker
    ? factChecks.find((check: any) => check.fact_checker.slug === selectedChecker)
    : null;

  // Handle delete
  const handleDelete = async () => {
    if (selectedChecker && confirm("Are you sure you want to delete this fact check?")) {
      try {
        await deleteFactCheck.mutateAsync(selectedChecker);
        // Refetch fact checks after deletion
        refetchFactChecks();
      } catch (error) {
        console.error("Failed to delete fact check:", error);
      }
    }
  };
  
  const handleRecreate = () => {
    // First delete, then navigate to create
    if (selectedChecker) {
      handleDelete().then(() => {
        window.location.href = `/posts/${postUid}/fact-checks/${selectedChecker}`;
      });
    }
  };
  
  const handleCreate = () => {
    if (selectedChecker) {
      // Navigate to the streaming fact check page
      window.location.href = `/posts/${postUid}/fact-checks/${selectedChecker}`;
    }
  };
  
  if (checksLoading || checkersLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fact Check Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-gray-500">Loading fact checkers...</p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fact Check Details</CardTitle>
      </CardHeader>

      {/* Fact Check Content - only show when a checker is selected */}
      {selectedChecker ? (
        <CardContent className="space-y-4">
          {/* Sub-header with fact checker name and action buttons */}
          <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                {selectedFactCheck 
                  ? `${selectedFactCheck.fact_checker.name}`
                  : `${factCheckers.find((fc: any) => fc.slug === selectedChecker)?.name || selectedChecker}`
                }
              </h3>
              {/* Action Buttons */}
              {selectedFactCheck && (
                <div className="flex gap-2">
                  <Link href={`/posts/${postUid}/fact-checks/${selectedChecker}`}>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      <Eye className="h-4 w-4" />
                      View Details
                    </Button>
                  </Link>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDelete}
                    disabled={deleteFactCheck.isPending}
                    className="flex items-center gap-2"
                  >
                    {deleteFactCheck.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                    {deleteFactCheck.isPending ? "Deleting..." : "Delete"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRecreate}
                    disabled={deleteFactCheck.isPending}
                    className="flex items-center gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Recreate
                  </Button>
                </div>
              )}
          </div>

          {/* Fact Check Display */}
          {selectedFactCheck ? (
            <div className="space-y-4">
              <FactCheckDisplay factCheck={selectedFactCheck} />
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">
                No fact check exists for this checker yet.
              </p>
              <Button
                onClick={handleCreate}
                className="flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Create Fact Check
              </Button>
            </div>
          )}
        </CardContent>
      ) : (
        <CardContent>
          <div className="text-center py-8">
            <p className="text-gray-600">Select a fact checker above to view details</p>
          </div>
        </CardContent>
      )}
    </Card>
  );
}