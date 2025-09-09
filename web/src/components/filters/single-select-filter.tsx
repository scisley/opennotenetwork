'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';

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

  const handleRadioChange = (value: string) => {
    onValueChange(value === '_all_' ? undefined : value);
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
          <RadioGroup 
            value={currentValue || '_all_'} 
            onValueChange={handleRadioChange}
            className="space-y-2"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="_all_" id={`${classifier.slug}-all`} />
              <Label 
                htmlFor={`${classifier.slug}-all`}
                className="text-sm font-normal cursor-pointer"
              >
                All values
              </Label>
            </div>
            {options.map((option: string) => {
              const valueData = availableValues?.find(v => v.value === option);
              // Find the label from the original schema
              const optionObj = schemaOptions.find((opt: any) => 
                (typeof opt === 'object' && opt.value === option) || opt === option
              );
              const label = typeof optionObj === 'object' ? (optionObj.label || option) : option;
              
              return (
                <div key={option} className="flex items-center space-x-2">
                  <RadioGroupItem 
                    value={option} 
                    id={`${classifier.slug}-${option}`} 
                  />
                  <Label 
                    htmlFor={`${classifier.slug}-${option}`}
                    className="text-sm font-normal cursor-pointer flex items-center gap-1"
                  >
                    {label}
                    {valueData && (
                      <span className="text-xs text-gray-500">
                        ({valueData.count})
                      </span>
                    )}
                  </Label>
                </div>
              );
            })}
          </RadioGroup>
        </div>
      )}
    </div>
  );
}