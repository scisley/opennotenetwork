'use client';

import { useEffect, useState } from 'react';
import { X, Filter, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { SingleSelectFilter } from './single-select-filter';
import { MultiSelectFilter } from './multi-select-filter';
import { HierarchicalFilter } from './hierarchical-filter';
import { useClassifiers } from '@/hooks/use-api';
import { FilterConfig } from '@/types/filters';

interface ClassificationFilterPanelProps {
  currentFilters: FilterConfig;
  onFiltersChange: (filters: FilterConfig) => void;
  className?: string;
}

export function ClassificationFilterPanel({
  currentFilters,
  onFiltersChange,
  className = '',
}: ClassificationFilterPanelProps) {
  const { data: classifiersData, isLoading } = useClassifiers();
  const [localFilters, setLocalFilters] = useState<FilterConfig>(currentFilters);

  // Sync local filters with props
  useEffect(() => {
    setLocalFilters(currentFilters);
  }, [currentFilters]);

  const handleFilterChange = (classifierSlug: string, update: Partial<FilterConfig[string]>) => {
    setLocalFilters(prevFilters => {
      const newFilters = { ...prevFilters };
      
      if (!newFilters[classifierSlug]) {
        newFilters[classifierSlug] = {};
      }
      
      // Check if we're explicitly clearing has_classification
      if ('has_classification' in update && (update.has_classification === false || update.has_classification === undefined)) {
        // If has_classification is being set to false/undefined, also clear values
        newFilters[classifierSlug] = {
          ...newFilters[classifierSlug],
          values: undefined,
          hierarchy: undefined,
          has_classification: update.has_classification,
        };
      } else {
        // Otherwise merge the update normally
        newFilters[classifierSlug] = {
          ...newFilters[classifierSlug],
          ...update,
        };
      }
      
      // Clean up empty filters
      if (
        !newFilters[classifierSlug].has_classification &&
        !newFilters[classifierSlug].values?.length &&
        !newFilters[classifierSlug].hierarchy?.level1
      ) {
        delete newFilters[classifierSlug];
      }
      
      return newFilters;
    });
  };

  const applyFilters = () => {
    onFiltersChange(localFilters);
  };

  const clearAllFilters = () => {
    setLocalFilters({});
    onFiltersChange({});
  };

  const activeFilterCount = Object.keys(localFilters).reduce((count, slug) => {
    const filter = localFilters[slug];
    let filterCount = 0;
    if (filter.has_classification) filterCount++;
    if (filter.values?.length) filterCount += filter.values.length;
    if (filter.hierarchy?.level1) filterCount++;
    if (filter.hierarchy?.level2) filterCount++;
    return count + filterCount;
  }, 0);

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

  // Group classifiers by type
  const singleSelectClassifiers = activeClassifiers.filter(
    c => c.output_schema?.type === 'single'
  );
  const multiSelectClassifiers = activeClassifiers.filter(
    c => c.output_schema?.type === 'multi'
  );
  const hierarchicalClassifiers = activeClassifiers.filter(
    c => c.output_schema?.type === 'hierarchical'
  );

  return (
    <div className={`${className} bg-white rounded-lg shadow-sm border flex flex-col h-full`}>
      <div className="p-4 border-b flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <h3 className="font-semibold">Classification Filters</h3>
            {activeFilterCount > 0 && (
              <Badge variant="secondary">{activeFilterCount} active</Badge>
            )}
          </div>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs"
            >
              Clear all
            </Button>
          )}
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-4">
          {/* Single Select Classifiers */}
          {singleSelectClassifiers.length > 0 && (
            <>
              <div className="space-y-4">
                {singleSelectClassifiers.map(classifier => {
                  const filterConfig = localFilters[classifier.slug] || {};
                  return (
                    <SingleSelectFilter
                      key={classifier.slug}
                      classifier={classifier}
                      currentValue={filterConfig.values?.[0]}
                      hasClassification={filterConfig.has_classification}
                      onValueChange={(value) =>
                        handleFilterChange(classifier.slug, {
                          values: value ? [value] : undefined,
                        })
                      }
                      onHasClassificationChange={(checked) =>
                        handleFilterChange(classifier.slug, {
                          has_classification: checked || undefined,
                        })
                      }
                    />
                  );
                })}
              </div>
              {(multiSelectClassifiers.length > 0 || hierarchicalClassifiers.length > 0) && (
                <Separator />
              )}
            </>
          )}

          {/* Multi Select Classifiers */}
          {multiSelectClassifiers.length > 0 && (
            <>
              <div className="space-y-4">
                {multiSelectClassifiers.map(classifier => {
                  // Use localFilters for display, not currentFilters
                  const filterConfig = localFilters[classifier.slug] || {};
                  return (
                    <MultiSelectFilter
                      key={classifier.slug}
                      classifier={classifier}
                      currentValues={filterConfig.values || []}
                      hasClassification={filterConfig.has_classification}
                      onValuesChange={(values) =>
                        handleFilterChange(classifier.slug, {
                          values: values.length > 0 ? values : undefined,
                        })
                      }
                      onHasClassificationChange={(checked) =>
                        handleFilterChange(classifier.slug, {
                          has_classification: checked || undefined,
                        })
                      }
                    />
                  );
                })}
              </div>
              {hierarchicalClassifiers.length > 0 && <Separator />}
            </>
          )}

          {/* Hierarchical Classifiers */}
          {hierarchicalClassifiers.length > 0 && (
            <div className="space-y-4">
              {hierarchicalClassifiers.map(classifier => {
                const filterConfig = localFilters[classifier.slug] || {};
                return (
                  <HierarchicalFilter
                    key={classifier.slug}
                    classifier={classifier}
                    currentHierarchy={filterConfig.hierarchy}
                    hasClassification={filterConfig.has_classification}
                    onHierarchyChange={(hierarchy) =>
                      handleFilterChange(classifier.slug, {
                        hierarchy: hierarchy.level1 ? hierarchy : undefined,
                      })
                    }
                    onHasClassificationChange={(checked) =>
                      handleFilterChange(classifier.slug, {
                        has_classification: checked || undefined,
                      })
                    }
                  />
                );
              })}
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t bg-gray-50 flex-shrink-0">
        <Button 
          onClick={applyFilters} 
          className="w-full" 
          size="sm"
          disabled={JSON.stringify(localFilters) === JSON.stringify(currentFilters)}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Apply Filters
        </Button>
      </div>
    </div>
  );
}