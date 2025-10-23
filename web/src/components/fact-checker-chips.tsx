"use client";

import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface FactChecker {
  slug: string;
  name: string;
  description?: string;
  is_active: boolean;
}

interface FactCheck {
  fact_checker: {
    slug: string;
    name: string;
  };
  status: "pending" | "processing" | "completed" | "failed";
}

interface FactCheckerChipsProps {
  factCheckers: FactChecker[];
  factChecks: FactCheck[];
  selectedChecker: string | null;
  onCheckerSelect: (slug: string) => void;
}

export function FactCheckerChips({
  factCheckers,
  factChecks,
  selectedChecker,
  onCheckerSelect,
}: FactCheckerChipsProps) {
  // Create a map for quick lookup of fact check status
  const factCheckMap = new Map(
    factChecks.map((check) => [check.fact_checker.slug, check])
  );

  return (
    <div className="flex flex-wrap gap-2">
      {factCheckers.map((checker) => {
        const factCheck = factCheckMap.get(checker.slug);
        const isSelected = selectedChecker === checker.slug;
        const hasFactCheck = !!factCheck;
        
        // Determine chip variant and styling based on state
        let variant: "default" | "secondary" | "outline" | "destructive" = "outline";
        let Icon = null;
        
        if (factCheck) {
          switch (factCheck.status) {
            case "completed":
              variant = "default";
              Icon = CheckCircle;
              break;
            case "processing":
              variant = "secondary";
              Icon = Loader2;
              break;
            case "failed":
              variant = "destructive";
              Icon = XCircle;
              break;
            case "pending":
              variant = "secondary";
              break;
          }
        }

        return (
          <Badge
            key={checker.slug}
            variant={variant}
            className={cn(
              "cursor-pointer transition-all",
              isSelected && "ring-2 ring-primary ring-offset-2",
              !hasFactCheck && "opacity-70 hover:opacity-100",
              factCheck?.status === "processing" && "animate-pulse"
            )}
            onClick={() => onCheckerSelect(checker.slug)}
          >
            {Icon && (
              <Icon
                className={cn(
                  "h-3 w-3 mr-1",
                  factCheck?.status === "processing" && "animate-spin"
                )}
              />
            )}
            {checker.name}
          </Badge>
        );
      })}
    </div>
  );
}