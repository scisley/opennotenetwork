'use client';

import { useEffect, useState } from 'react';
import { Filter, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { SingleSelectFilter } from './single-select-filter';
import { MultiSelectFilter } from './multi-select-filter';
import { DateRangeFilter, DateRangeValue } from './date-range-filter';
import { FactCheckStatusFilter, FactCheckStatus } from './fact-check-status-filter';
import { NoteStatusFilter, NoteStatus } from './note-status-filter';
import { useClassifiers } from '@/hooks/use-api';
import { FilterConfig } from '@/types/filters';

export interface StatusFilters {
  hasFactCheck?: boolean;
  hasNote?: boolean;
  factCheckStatus?: FactCheckStatus;
  noteStatus?: NoteStatus;
  dateRange?: DateRangeValue;
}

interface ClassificationFilterPanelProps {
  currentFilters: FilterConfig;
  onFiltersChange: (filters: FilterConfig) => void;
  currentStatusFilters?: StatusFilters;
  onStatusFiltersChange?: (filters: StatusFilters) => void;
  onBothFiltersChange?: (filters: FilterConfig, statusFilters: StatusFilters) => void;
  className?: string;
}

export function ClassificationFilterPanel({
  currentFilters,
  onFiltersChange,
  currentStatusFilters = {},
  onStatusFiltersChange,
  onBothFiltersChange,
  className = '',
}: ClassificationFilterPanelProps) {
  const { data: classifiersData, isLoading } = useClassifiers();
  const [localFilters, setLocalFilters] = useState<FilterConfig>(currentFilters);
  const [localStatusFilters, setLocalStatusFilters] = useState<StatusFilters>(currentStatusFilters);

  // Sync local filters with props
  useEffect(() => {
    setLocalFilters(currentFilters);
  }, [currentFilters]);

  useEffect(() => {
    setLocalStatusFilters(currentStatusFilters);
  }, [currentStatusFilters]);

  const handleFilterChange = (classifierSlug: string, update: Partial<FilterConfig[string]>) => {
    setLocalFilters(prevFilters => {
      const newFilters = { ...prevFilters };
      
      if (!newFilters[classifierSlug]) {
        newFilters[classifierSlug] = {};
      }
      
      // Merge the update
      newFilters[classifierSlug] = {
        ...newFilters[classifierSlug],
        ...update,
      };

      // Clean up empty filters - only keep if there are actual values
      if (
        !newFilters[classifierSlug].values?.length &&
        !newFilters[classifierSlug].hierarchy?.level1
      ) {
        delete newFilters[classifierSlug];
      }
      
      return newFilters;
    });
  };

  const applyFilters = () => {
    // Use combined handler if available to avoid race conditions
    if (onBothFiltersChange) {
      onBothFiltersChange(localFilters, localStatusFilters);
    } else {
      // Fall back to individual handlers
      onFiltersChange(localFilters);
      if (onStatusFiltersChange) {
        onStatusFiltersChange(localStatusFilters);
      }
    }
  };

  const clearAllFilters = () => {
    // Only clear local state, don't call parent handlers
    // The Apply Filters button will handle the actual update
    setLocalFilters({});
    setLocalStatusFilters({});
  };

  const activeFilterCount = Object.keys(localFilters).reduce((count, slug) => {
    const filter = localFilters[slug];
    let filterCount = 0;
    // Only count actual selected values, not just "has_classification"
    if (filter.values?.length) filterCount += filter.values.length;
    if (filter.hierarchy?.level1) filterCount++;
    if (filter.hierarchy?.level2) filterCount++;
    return count + filterCount;
  }, 0) +
  (localStatusFilters.hasFactCheck ? 1 : 0) +
  (localStatusFilters.hasNote ? 1 : 0) +
  (localStatusFilters.factCheckStatus ? 1 : 0) +
  (localStatusFilters.noteStatus ? 1 : 0) +
  (localStatusFilters.dateRange?.after || localStatusFilters.dateRange?.before ? 1 : 0);

  if (isLoading) {
    return (
      <div className={`${className} p-4`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-2/3"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const classifiers = classifiersData?.classifiers || [];
  const activeClassifiers = classifiers.filter(c => c.is_active);

  // Group classifiers by logical categories
  const domainClassifier = activeClassifiers.find(c => c.slug === 'domain-classifier-v1');
  const partisanTiltClassifier = activeClassifiers.find(c => c.slug === 'partisan-tilt-v1');
  const mediaTypeClassifier = activeClassifiers.find(c => c.slug === 'media-type-v1');
  const tweetTypeClassifier = activeClassifiers.find(c => c.slug === 'tweet-type-v1');
  const clarityClassifier = activeClassifiers.find(c => c.slug === 'clarity-v1');

  return (
    <div className={`${className} bg-white rounded-lg shadow-sm border flex flex-col h-full`}>
      <div className="p-4 border-b flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <h3 className="font-semibold">Filters</h3>
            <Badge
              variant="secondary"
              className={activeFilterCount > 0 ? '' : 'invisible'}
            >
              {activeFilterCount} active
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className={`text-xs ${activeFilterCount > 0 ? '' : 'invisible'}`}
          >
            Clear all
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-6">
          {/* Group 1: Domain & Political */}
          {(domainClassifier || partisanTiltClassifier) && (
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Domain & Political</h3>
              {domainClassifier && (
                <MultiSelectFilter
                  classifier={domainClassifier}
                  currentValues={localFilters[domainClassifier.slug]?.values || []}
                  hasClassification={localFilters[domainClassifier.slug]?.has_classification}
                  onValuesChange={(values) =>
                    handleFilterChange(domainClassifier.slug, {
                      values: values.length > 0 ? values : undefined,
                    })
                  }
                  onHasClassificationChange={(checked) =>
                    handleFilterChange(domainClassifier.slug, {
                      has_classification: checked || undefined,
                    })
                  }
                />
              )}
              {partisanTiltClassifier && (
                <SingleSelectFilter
                  classifier={partisanTiltClassifier}
                  currentValue={localFilters[partisanTiltClassifier.slug]?.values?.[0]}
                  hasClassification={localFilters[partisanTiltClassifier.slug]?.has_classification}
                  onValueChange={(value) =>
                    handleFilterChange(partisanTiltClassifier.slug, {
                      values: value ? [value] : undefined,
                    })
                  }
                  onHasClassificationChange={(checked) =>
                    handleFilterChange(partisanTiltClassifier.slug, {
                      has_classification: checked || undefined,
                    })
                  }
                />
              )}
            </div>
          )}

          {/* Separator */}
          {(domainClassifier || partisanTiltClassifier) && (mediaTypeClassifier || tweetTypeClassifier) && <Separator />}

          {/* Group 2: Content Type */}
          {(mediaTypeClassifier || tweetTypeClassifier) && (
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Content Type</h3>
              {mediaTypeClassifier && (
                <MultiSelectFilter
                  classifier={mediaTypeClassifier}
                  currentValues={localFilters[mediaTypeClassifier.slug]?.values || []}
                  hasClassification={localFilters[mediaTypeClassifier.slug]?.has_classification}
                  onValuesChange={(values) =>
                    handleFilterChange(mediaTypeClassifier.slug, {
                      values: values.length > 0 ? values : undefined,
                    })
                  }
                  onHasClassificationChange={(checked) =>
                    handleFilterChange(mediaTypeClassifier.slug, {
                      has_classification: checked || undefined,
                    })
                  }
                />
              )}
              {tweetTypeClassifier && (
                <SingleSelectFilter
                  classifier={tweetTypeClassifier}
                  currentValue={localFilters[tweetTypeClassifier.slug]?.values?.[0]}
                  hasClassification={localFilters[tweetTypeClassifier.slug]?.has_classification}
                  onValueChange={(value) =>
                    handleFilterChange(tweetTypeClassifier.slug, {
                      values: value ? [value] : undefined,
                    })
                  }
                  onHasClassificationChange={(checked) =>
                    handleFilterChange(tweetTypeClassifier.slug, {
                      has_classification: checked || undefined,
                    })
                  }
                />
              )}
            </div>
          )}

          {/* Separator */}
          {((mediaTypeClassifier || tweetTypeClassifier) && clarityClassifier) && <Separator />}

          {/* Group 3: Quality Assessment */}
          {clarityClassifier && (
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Quality Assessment</h3>
              <SingleSelectFilter
                classifier={clarityClassifier}
                currentValue={localFilters[clarityClassifier.slug]?.values?.[0]}
                hasClassification={localFilters[clarityClassifier.slug]?.has_classification}
                onValueChange={(value) =>
                  handleFilterChange(clarityClassifier.slug, {
                    values: value ? [value] : undefined,
                  })
                }
                onHasClassificationChange={(checked) =>
                  handleFilterChange(clarityClassifier.slug, {
                    has_classification: checked || undefined,
                  })
                }
              />
            </div>
          )}

          <Separator />

          {/* Processing Status */}
          <FactCheckStatusFilter
            value={localStatusFilters.factCheckStatus}
            onChange={(value) => {
              setLocalStatusFilters(prev => ({
                ...prev,
                factCheckStatus: value,
                // Clear old boolean filters when using new status filter
                hasFactCheck: undefined,
                hasNote: undefined,
              }));
            }}
          />

          <Separator />

          {/* Note Status */}
          <NoteStatusFilter
            value={localStatusFilters.noteStatus}
            onChange={(value) => {
              setLocalStatusFilters(prev => ({
                ...prev,
                noteStatus: value,
              }));
            }}
          />

          <Separator />

          {/* Time Filter */}
          <DateRangeFilter
            value={localStatusFilters.dateRange || {}}
            onChange={(value) => {
              setLocalStatusFilters(prev => ({
                ...prev,
                dateRange: (value.after || value.before) ? value : undefined,
              }));
            }}
          />
        </div>
      </ScrollArea>

      <div className="p-4 border-t bg-gray-50 flex-shrink-0">
        <Button 
          onClick={applyFilters} 
          className="w-full" 
          size="sm"
          disabled={
            JSON.stringify(localFilters) === JSON.stringify(currentFilters) &&
            JSON.stringify(localStatusFilters) === JSON.stringify(currentStatusFilters)
          }
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Apply Filters
        </Button>
      </div>
    </div>
  );
}