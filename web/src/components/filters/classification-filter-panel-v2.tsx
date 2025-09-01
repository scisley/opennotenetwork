'use client';

import { Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { SingleSelectFilter } from './single-select-filter-v2';
import { MultiSelectFilter } from './multi-select-filter-v2';
import { useClassifiers } from '@/hooks/use-api';
import { FilterConfig } from '@/types/filters';
import { countActiveFilters } from '@/lib/filter-utils';

interface ClassificationFilterPanelProps {
  filters: FilterConfig;
  onFiltersChange: (filters: FilterConfig) => void;
  className?: string;
}

export function ClassificationFilterPanel({
  filters,
  onFiltersChange,
  className = '',
}: ClassificationFilterPanelProps) {
  const { data: classifiersData, isLoading } = useClassifiers();

  const updateFilter = (slug: string, value: any) => {
    const newFilters = { ...filters };
    
    if (value === undefined || value === null || 
        (Array.isArray(value) && value.length === 0)) {
      delete newFilters[slug];
    } else {
      newFilters[slug] = { values: Array.isArray(value) ? value : [value] };
    }
    
    onFiltersChange(newFilters);
  };

  const clearAllFilters = () => {
    onFiltersChange({});
  };

  const activeFilterCount = Object.keys(filters).reduce(
    (sum, slug) => sum + countActiveFilters(filters[slug]), 
    0
  );

  if (isLoading) {
    return (
      <div className={`${className} p-4`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-2/3"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const classifiers = classifiersData?.classifiers.filter(c => c.is_active) || [];
  
  // Group by type
  const classifiersByType = {
    single: classifiers.filter(c => c.output_schema?.type === 'single'),
    multi: classifiers.filter(c => c.output_schema?.type === 'multi'),
  };

  return (
    <div className={`${className} bg-white rounded-lg shadow-sm border`}>
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <h3 className="font-semibold">Filters</h3>
            {activeFilterCount > 0 && (
              <Badge variant="secondary">{activeFilterCount}</Badge>
            )}
          </div>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </div>

      <ScrollArea className="h-[600px]">
        <div className="p-4 space-y-4">
          {/* Single Select */}
          {classifiersByType.single.map(classifier => (
            <SingleSelectFilter
              key={classifier.slug}
              classifier={classifier}
              value={filters[classifier.slug]?.values?.[0]}
              onChange={(value) => updateFilter(classifier.slug, value)}
            />
          ))}
          
          {classifiersByType.single.length > 0 && 
           classifiersByType.multi.length > 0 && <Separator />}
          
          {/* Multi Select */}
          {classifiersByType.multi.map(classifier => (
            <MultiSelectFilter
              key={classifier.slug}
              classifier={classifier}
              values={filters[classifier.slug]?.values || []}
              onChange={(values) => updateFilter(classifier.slug, values)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}