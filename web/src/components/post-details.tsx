"use client";

import { useState } from "react";
import { Classification, Classifier } from "@/types/api";
import { useClassifiers } from "@/hooks/use-api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface PostDetailsProps {
  classifications: Classification[];
}

interface ClassificationModal {
  isOpen: boolean;
  classification: Classification | null;
  displayValue: any;
}

export function PostDetails({ classifications }: PostDetailsProps) {
  const [modal, setModal] = useState<ClassificationModal>({
    isOpen: false,
    classification: null,
    displayValue: null,
  });

  // Fetch classifiers to get descriptions
  const { data: classifiersData } = useClassifiers();
  const classifiers = classifiersData?.classifiers || [];

  // Create a map of classifier slug to classifier for quick lookup
  const classifierMap = classifiers.reduce((map, clf) => {
    map[clf.slug] = clf;
    return map;
  }, {} as Record<string, Classifier>);

  if (!classifications || classifications.length === 0) {
    return null;
  }

  // Group classifications with custom logic
  const grouped = classifications.reduce((acc, clf) => {
    let group = "Other";

    const displayName = clf.classifier_display_name?.toLowerCase() || "";
    const slug = clf.classifier_slug?.toLowerCase() || "";

    // Get the classification value(s) to check
    const data = clf.classification_data;
    let classificationValues: string[] = [];

    if (data.type === "single" && data.value) {
      classificationValues = [data.value.toLowerCase()];
    } else if (data.type === "multi" && data.values) {
      classificationValues = data.values.map((v: any) => v.value.toLowerCase());
    } else if (data.type === "hierarchical" && data.levels) {
      classificationValues = data.levels.map((l: any) => l.value.toLowerCase());
    }

    // Check if any classification value or classifier name indicates subject matter
    const isSubjectMatter = classificationValues.some(v =>
      v.includes("media") ||
      v.includes("politics") ||
      v.includes("economy") ||
      v.includes("business") ||
      v.includes("law") ||
      v.includes("science") ||
      v.includes("health") ||
      v.includes("climate") ||
      v.includes("attribution") ||
      v.includes("government") ||
      v.includes("regulation") ||
      v.includes("crime") ||
      v.includes("safety") ||
      v.includes("news")
    ) || slug.includes("domain") || displayName.includes("domain");

    // Check if any classification value or classifier name indicates partisan tilt
    const isPartisanTilt = classificationValues.some(v =>
      v.includes("right") ||
      v.includes("left") ||
      v.includes("neutral") ||
      v.includes("partisan")
    ) || slug.includes("partisan") || displayName.includes("partisan") || displayName.includes("tilt");

    if (isSubjectMatter) {
      group = "Subject Matter";
    } else if (isPartisanTilt) {
      group = "Partisan Tilt";
    } else {
      group = "Other";
    }

    if (!acc[group]) {
      acc[group] = [];
    }
    acc[group].push(clf);
    return acc;
  }, {} as Record<string, Classification[]>);

  // Define the order of groups
  const groupOrder = ["Subject Matter", "Partisan Tilt", "Other"];
  const orderedGroups = groupOrder.filter(group => group in grouped);

  const getClassificationDisplay = (clf: Classification) => {
    const data = clf.classification_data;
    const schema = clf.output_schema;

    if (data.type === "single" && data.value) {
      const choice = schema?.choices?.find((c: any) => c.value === data.value);
      if (choice) {
        return {
          icon: choice.icon || "📊",
          label: choice.label || data.value,
          value: data.value,
          reason: data.reason || null,  // Extract reason from single classification
          confidence: data.confidence,
          color: choice.color,
        };
      }
      return {
        icon: "📊",
        label: data.value,
        value: data.value,
        reason: data.reason || null,
        confidence: data.confidence,
      };
    }

    if (data.type === "multi" && data.values && data.values.length > 0) {
      // For multi, show all values with their icons and reasons
      return data.values.map(v => {
        const choice = schema?.choices?.find((c: any) =>
          typeof c === "string" ? c === v.value : c.value === v.value
        );
        if (typeof choice === "object" && choice !== null) {
          return {
            icon: choice.icon || "📊",
            label: choice.label || v.value,
            value: v.value,
            reason: v.reason || null,  // Extract reason from each value
            confidence: v.confidence,
            color: choice.color,
          };
        }
        return {
          icon: "📊",
          label: v.value,
          value: v.value,
          reason: v.reason || null,  // Extract reason from each value
          confidence: v.confidence,
        };
      });
    }

    if (data.type === "hierarchical" && data.levels && data.levels.length > 0) {
      // Show the deepest level for hierarchical
      const lastLevel = data.levels[data.levels.length - 1];
      return {
        icon: "📊",
        label: lastLevel.value,
        value: lastLevel.value,
        reason: lastLevel.reason || null,  // Extract reason from hierarchical level
        confidence: lastLevel.confidence,
      };
    }

    return null;
  };

  const openModal = (clf: Classification, displayValue: any) => {
    setModal({
      isOpen: true,
      classification: clf,
      displayValue: displayValue,
    });
  };

  const closeModal = () => {
    setModal({
      isOpen: false,
      classification: null,
      displayValue: null,
    });
  };

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-white border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Info className="h-5 w-5" />
            Post Details
          </h3>
        </div>

        <div className="p-6">
          <TooltipProvider>
            <div className="space-y-4">
              {orderedGroups.map((groupName) => (
                <div key={groupName}>
                  <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                    {groupName}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {grouped[groupName].map((clf) => {
                      const display = getClassificationDisplay(clf);
                      if (!display) return null;

                      // Handle multi-value classifications
                      if (Array.isArray(display)) {
                        return display.map((item, idx) => (
                          <Tooltip key={`${clf.classifier_slug || idx}-${idx}`}>
                            <TooltipTrigger asChild>
                              <button
                                onClick={() => openModal(clf, item)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 cursor-pointer transition-colors"
                              >
                                <span className="text-lg" role="img" aria-label={item.label}>
                                  {item.icon}
                                </span>
                                <span className="text-sm text-gray-700">
                                  {item.label}
                                </span>
                              </button>
                            </TooltipTrigger>
                            {item.reason && (
                              <TooltipContent className="max-w-xs">
                                <p className="text-sm">{item.reason}</p>
                              </TooltipContent>
                            )}
                          </Tooltip>
                        ));
                      }

                      // Handle single-value classifications
                      return (
                        <Tooltip key={clf.classifier_slug || Math.random()}>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => openModal(clf, display)}
                              className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 cursor-pointer transition-colors"
                            >
                              <span className="text-lg" role="img" aria-label={display.label}>
                                {display.icon}
                              </span>
                              <span className="text-sm text-gray-700">
                                {display.label}
                              </span>
                            </button>
                          </TooltipTrigger>
                          {display.reason && (
                            <TooltipContent className="max-w-xs">
                              <p className="text-sm">{display.reason}</p>
                            </TooltipContent>
                          )}
                        </Tooltip>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </TooltipProvider>
        </div>
      </div>

      {/* Modal for showing classification details */}
      <Dialog open={modal.isOpen} onOpenChange={closeModal}>
        <DialogContent className="max-w-md w-[calc(100%-2rem)]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {modal.displayValue && (
                <>
                  <span className="text-xl" role="img" aria-label={modal.displayValue.label}>
                    {modal.displayValue.icon}
                  </span>
                  <span>{modal.displayValue.label}</span>
                </>
              )}
            </DialogTitle>
            <DialogDescription className="sr-only">
              Classification details and reasoning
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {/* Show classifier name */}
            {modal.classification?.classifier_display_name && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-1">
                  Classifier
                </div>
                <div className="text-sm text-gray-600">
                  {modal.classification.classifier_display_name}
                </div>
              </div>
            )}
            {/* Show classifier description if available */}
            {modal.classification && classifierMap[modal.classification.classifier_slug]?.description && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-1">
                  Description
                </div>
                <div className="text-sm text-gray-600 leading-relaxed">
                  {classifierMap[modal.classification.classifier_slug].description}
                </div>
              </div>
            )}
            {/* Show the specific reasoning for this classification value */}
            {modal.displayValue?.reason && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-1">
                  Reasoning
                </div>
                <div className="text-sm text-gray-600 leading-relaxed">
                  {modal.displayValue.reason}
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}