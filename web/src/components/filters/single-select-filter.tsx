'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface SingleSelectFilterProps {
  classifier: {
    slug: string;
    display_name: string;
    output_schema: any;
  };
  currentValue?: string;
  hasClassification?: boolean;
  onValueChange: (value: string | undefined) => void;
  onHasClassificationChange: (checked: boolean) => void;
  availableValues?: { value: string; count: number }[];
}

export function SingleSelectFilter({
  classifier,
  currentValue,
  hasClassification,
  onValueChange,
  onHasClassificationChange,
  availableValues,
}: SingleSelectFilterProps) {
  const [isExpanded, setIsExpanded] = useState(hasClassification || !!currentValue);
  
  // Extract options from the schema - handle both 'options' and 'choices' fields
  const schemaOptions = classifier.output_schema?.options || classifier.output_schema?.choices || [];
  const options = schemaOptions.map((opt: any) => 
    typeof opt === 'string' ? opt : (opt.value || opt)
  );

  const handleToggle = (checked: boolean) => {
    setIsExpanded(checked);
    // When toggling, also update the "has classification" filter
    onHasClassificationChange(checked);
    // When collapsing, clear any selected value
    if (!checked && currentValue) {
      onValueChange(undefined);
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
        <div className="pl-6 space-y-2">
          <Select 
            value={currentValue || '_all_'} 
            onValueChange={(value) => onValueChange(value === '_all_' ? undefined : value)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a value..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all_">All values</SelectItem>
              {options.map((option: string) => {
                const valueData = availableValues?.find(v => v.value === option);
                // Find the label from the original schema
                const optionObj = schemaOptions.find((opt: any) => 
                  (typeof opt === 'object' && opt.value === option) || opt === option
                );
                const label = typeof optionObj === 'object' ? (optionObj.label || option) : option;
                
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
  );
}