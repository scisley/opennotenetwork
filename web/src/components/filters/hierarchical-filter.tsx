'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface HierarchicalFilterProps {
  classifier: {
    slug: string;
    display_name: string;
    output_schema: any;
  };
  currentHierarchy?: {
    level1?: string;
    level2?: string;
  };
  hasClassification?: boolean;
  onHierarchyChange: (hierarchy: { level1?: string; level2?: string }) => void;
  onHasClassificationChange: (checked: boolean) => void;
  availableValues?: {
    level1: { value: string; count: number }[];
    level2: { [parentKey: string]: { value: string; count: number }[] };
  };
}

export function HierarchicalFilter({
  classifier,
  currentHierarchy = {},
  hasClassification,
  onHierarchyChange,
  onHasClassificationChange,
  availableValues,
}: HierarchicalFilterProps) {
  const [isExpanded, setIsExpanded] = useState(
    hasClassification || !!currentHierarchy.level1
  );

  // Handle different hierarchical schema formats
  const schema = classifier.output_schema;
  let level1Options: string[] = [];
  let level2Options: string[] = [];
  
  if (schema?.hierarchy) {
    // Format 1: hierarchy object with keys as level1 and values as level2 arrays
    level1Options = Object.keys(schema.hierarchy);
    level2Options = currentHierarchy.level1 ? (schema.hierarchy[currentHierarchy.level1] || []) : [];
  } else if (schema?.levels && Array.isArray(schema.levels)) {
    // Format 2: levels array with choices and choices_by_parent
    const level1Data = schema.levels[0];
    const level2Data = schema.levels[1];
    
    if (level1Data?.choices) {
      level1Options = level1Data.choices.map((c: any) => c.value || c);
    }
    
    if (currentHierarchy.level1 && level2Data) {
      if (level2Data.choices_by_parent && level2Data.choices_by_parent[currentHierarchy.level1]) {
        level2Options = level2Data.choices_by_parent[currentHierarchy.level1].map((c: any) => c.value || c);
      } else if (level2Data.choices) {
        level2Options = level2Data.choices.map((c: any) => c.value || c);
      }
    }
  }

  const handleLevel1Change = (value: string | undefined) => {
    onHierarchyChange({
      level1: value,
      level2: undefined, // Reset level2 when level1 changes
    });
  };

  const handleLevel2Change = (value: string | undefined) => {
    onHierarchyChange({
      ...currentHierarchy,
      level2: value,
    });
  };

  const handleToggle = (checked: boolean) => {
    setIsExpanded(checked);
    // When toggling, also update the "has classification" filter
    onHasClassificationChange(checked);
    // When collapsing, clear any selected hierarchy values
    if (!checked && (currentHierarchy.level1 || currentHierarchy.level2)) {
      onHierarchyChange({});
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleToggle(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium hover:text-gray-700"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          {classifier.display_name}
        </button>
        <Checkbox
          id={`filter-${classifier.slug}`}
          checked={isExpanded}
          onCheckedChange={handleToggle}
          title="Filter for posts with this classification"
        />
      </div>

      {isExpanded && (
        <div className="pl-6 space-y-3">
          <div>
            <Label className="text-xs text-gray-600 mb-1">Level 1</Label>
            <Select
              value={currentHierarchy.level1 || '_all_'}
              onValueChange={(value) => handleLevel1Change(value === '_all_' ? undefined : value)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select level 1..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all_">All</SelectItem>
                {level1Options.map((option) => {
                  const valueData = availableValues?.level1?.find(
                    (v) => v.value === option
                  );
                  // Find label from schema
                  let label = option;
                  if (schema?.levels?.[0]?.choices) {
                    const choice = schema.levels[0].choices.find((c: any) => c.value === option);
                    label = choice?.label || option;
                  }
                  
                  return (
                    <SelectItem key={option} value={option}>
                      {label}
                      {valueData && (
                        <span className="ml-2 text-xs text-gray-500">
                          ({valueData.count})
                        </span>
                      )}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          {currentHierarchy.level1 && level2Options.length > 0 && (
            <div>
              <Label className="text-xs text-gray-600 mb-1">Level 2</Label>
              <Select
                value={currentHierarchy.level2 || '_all_'}
                onValueChange={(value) => handleLevel2Change(value === '_all_' ? undefined : value)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select level 2..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all_">All</SelectItem>
                  {level2Options.map((option: string) => {
                    const valueData =
                      availableValues?.level2?.[currentHierarchy.level1!]?.find(
                        (v) => v.value === option
                      );
                    // Find label from schema
                    let label = option;
                    if (schema?.levels?.[1]) {
                      const level2Data = schema.levels[1];
                      let choice;
                      if (level2Data.choices_by_parent && currentHierarchy.level1) {
                        choice = level2Data.choices_by_parent[currentHierarchy.level1]?.find((c: any) => c.value === option);
                      } else if (level2Data.choices) {
                        choice = level2Data.choices.find((c: any) => c.value === option);
                      }
                      label = choice?.label || option;
                    }
                    
                    return (
                      <SelectItem key={option} value={option}>
                        {label}
                        {valueData && (
                          <span className="ml-2 text-xs text-gray-500">
                            ({valueData.count})
                          </span>
                        )}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}