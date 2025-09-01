'use client';

import { BaseFilter } from './base-filter';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { extractOptions } from '@/lib/filter-utils';

interface MultiSelectFilterProps {
  classifier: {
    slug: string;
    display_name: string;
    output_schema: any;
  };
  values?: string[];
  onChange: (values: string[]) => void;
}

export function MultiSelectFilter({
  classifier,
  values = [],
  onChange,
}: MultiSelectFilterProps) {
  const options = extractOptions(classifier.output_schema);

  const handleActiveChange = (active: boolean) => {
    if (!active) {
      onChange([]);
    }
  };

  const toggleValue = (value: string) => {
    if (values.includes(value)) {
      onChange(values.filter(v => v !== value));
    } else {
      onChange([...values, value]);
    }
  };

  return (
    <BaseFilter
      title={classifier.display_name}
      isActive={values.length > 0}
      onActiveChange={handleActiveChange}
      badge={values.length > 0 && (
        <Badge variant="secondary" className="ml-2">
          {values.length}
        </Badge>
      )}
    >
      <ScrollArea className="h-48 border rounded-md p-3">
        <div className="space-y-2">
          {options.map((option) => (
            <label 
              key={option.value}
              className="flex items-center space-x-2 cursor-pointer"
            >
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                checked={values.includes(option.value)}
                onChange={() => toggleValue(option.value)}
              />
              <span className="text-sm font-normal flex-1 select-none">
                {option.icon && <span className="mr-1">{option.icon}</span>}
                {option.label}
              </span>
            </label>
          ))}
        </div>
      </ScrollArea>
      {values.length > 0 && (
        <button
          onClick={() => onChange([])}
          className="mt-2 text-xs text-blue-600 hover:text-blue-800"
        >
          Clear all
        </button>
      )}
    </BaseFilter>
  );
}