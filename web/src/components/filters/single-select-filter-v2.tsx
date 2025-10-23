'use client';

import { BaseFilter } from './base-filter';
import { extractOptions } from '@/lib/filter-utils';
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
  value?: string;
  onChange: (value: string | undefined) => void;
}

export function SingleSelectFilter({
  classifier,
  value,
  onChange,
}: SingleSelectFilterProps) {
  const options = extractOptions(classifier.output_schema);
  const hasValue = !!value;

  const handleActiveChange = (active: boolean) => {
    if (!active) {
      onChange(undefined);
    }
  };

  return (
    <BaseFilter
      title={classifier.display_name}
      isActive={hasValue}
      onActiveChange={handleActiveChange}
    >
      <Select 
        value={value || '_all_'} 
        onValueChange={(val) => onChange(val === '_all_' ? undefined : val)}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select a value..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_all_">All values</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.icon && <span className="mr-1">{option.icon}</span>}
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </BaseFilter>
  );
}