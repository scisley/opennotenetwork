// Utility functions for filter components

export interface OptionData {
  value: string;
  label: string;
  icon?: string;
}

/**
 * Extract options from a classifier schema
 * Handles both 'options' and 'choices' fields
 */
export function extractOptions(schema: any): OptionData[] {
  const rawOptions = schema?.options || schema?.choices || [];
  
  return rawOptions.map((opt: any): OptionData => {
    if (typeof opt === 'string') {
      return { value: opt, label: opt };
    }
    return {
      value: opt.value || opt,
      label: opt.label || opt.value || opt,
      icon: opt.icon
    };
  });
}

/**
 * Extract hierarchical levels from a schema
 */
export function extractHierarchicalLevels(schema: any): Array<{ name: string; options: OptionData[] }> {
  const levels = schema?.levels || [];
  
  return levels.map((level: any) => ({
    name: level.name || `Level ${level.level}`,
    options: extractOptions(level)
  }));
}

/**
 * Check if any filter values are active
 */
export function hasActiveFilters(filter: any): boolean {
  return !!(
    filter?.has_classification ||
    filter?.values?.length ||
    filter?.hierarchy?.level1
  );
}

/**
 * Count active filter criteria
 */
export function countActiveFilters(filter: any): number {
  let count = 0;
  if (filter?.has_classification) count++;
  if (filter?.values?.length) count += filter.values.length;
  if (filter?.hierarchy?.level1) count++;
  if (filter?.hierarchy?.level2) count++;
  return count;
}