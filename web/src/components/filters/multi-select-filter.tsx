'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';

interface MultiSelectFilterProps {
  classifier: {
    slug: string;
    display_name: string;
    description?: string | null;  // Accept null from database
    output_schema: any;
  };
  currentValues?: string[];
  hasClassification?: boolean;
  onValuesChange: (values: string[]) => void;
  onHasClassificationChange: (checked: boolean) => void;
  availableValues?: { value: string; count: number }[];
}

export function MultiSelectFilter({
  classifier,
  currentValues = [],
  hasClassification,
  onValuesChange,
  onHasClassificationChange,
  availableValues,
}: MultiSelectFilterProps) {
  const [isExpanded, setIsExpanded] = useState(hasClassification || currentValues.length > 0);
  
  // Update expansion state when props change
  useEffect(() => {
    setIsExpanded(hasClassification || currentValues.length > 0);
  }, [hasClassification, currentValues.length]);
  
  // Extract options from the schema - handle both 'options' and 'choices' fields
  const schemaOptions = classifier.output_schema?.options || classifier.output_schema?.choices || [];
  const options = schemaOptions.map((opt: any) => 
    typeof opt === 'string' ? opt : (opt.value || opt)
  );

  const handleToggle = (checked: boolean) => {
    setIsExpanded(checked);
    // When toggling, also update the "has classification" filter
    onHasClassificationChange(checked);
    // When collapsing, clear any selected values
    if (!checked && currentValues.length > 0) {
      onValuesChange([]);
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
          {currentValues.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {currentValues.length}
            </Badge>
          )}
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
          {classifier.description && (
            <p className="text-xs text-gray-500 mb-2">{classifier.description}</p>
          )}
          <ScrollArea className="h-48 border rounded-md p-3">
            <div className="space-y-2">
              {options.map((option: string) => {
                const valueData = availableValues?.find(v => v.value === option);
                // Find the label and icon from the original schema
                const optionObj = schemaOptions.find((opt: any) => 
                  (typeof opt === 'object' && opt.value === option) || opt === option
                );
                const label = typeof optionObj === 'object' ? (optionObj.label || option) : option;
                const icon = typeof optionObj === 'object' ? optionObj.icon : null;
                const isChecked = currentValues.includes(option);
                
                return (
                  <label 
                    key={`${classifier.slug}-${option}`} 
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      checked={isChecked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          onValuesChange([...currentValues, option]);
                        } else {
                          onValuesChange(currentValues.filter(v => v !== option));
                        }
                      }}
                    />
                    <span className="text-sm font-normal flex-1 select-none">
                      {icon && <span className="mr-1">{icon}</span>}
                      {label}
                      {valueData && (
                        <span className="ml-2 text-xs text-gray-500">
                          ({valueData.count})
                        </span>
                      )}
                    </span>
                  </label>
                );
              })}
            </div>
          </ScrollArea>
          {currentValues.length > 0 && (
            <button
              onClick={() => onValuesChange([])}
              className="mt-2 text-xs text-blue-600 hover:text-blue-800"
            >
              Clear all
            </button>
          )}
        </div>
      )}
    </div>
  );
}