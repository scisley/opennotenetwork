"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFactCheckers } from "@/hooks/use-api";
import { FactCheckerChips } from "./fact-checker-chips";

interface FactCheckerSelectorProps {
  factChecks: any[];
  selectedChecker: string | null;
  onCheckerSelect: (slug: string) => void;
}

export function FactCheckerSelector({
  factChecks,
  selectedChecker,
  onCheckerSelect,
}: FactCheckerSelectorProps) {
  const { data: factCheckersData, isLoading: checkersLoading } = useFactCheckers();

  const factCheckers = factCheckersData?.fact_checkers || [];

  if (checkersLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Select Fact Checker</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-gray-500">Loading fact checkers...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Select Fact Checker</CardTitle>
      </CardHeader>
      <CardContent>
        {factCheckers.length > 0 ? (
          <div className="space-y-2">
            <p className="text-sm text-gray-600">
              Select a fact checker to view or manage its results. Highlighted checkers have existing fact checks.
            </p>
            <FactCheckerChips
              factCheckers={factCheckers}
              factChecks={factChecks}
              selectedChecker={selectedChecker}
              onCheckerSelect={onCheckerSelect}
            />
          </div>
        ) : (
          <p className="text-sm text-gray-500">No fact checkers available</p>
        )}
      </CardContent>
    </Card>
  );
}
