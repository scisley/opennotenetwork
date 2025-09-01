export interface ClassificationFilter {
  classifierSlug: string;
  hasClassification?: boolean;
  values?: string[];
  hierarchy?: {
    level1?: string;
    level2?: string;
  };
}

export interface FilterConfig {
  [classifierSlug: string]: {
    has_classification?: boolean;
    values?: string[];
    hierarchy?: {
      level1?: string;
      level2?: string;
    };
  };
}

export interface FilterPanelProps {
  onFiltersChange: (filters: FilterConfig) => void;
  currentFilters: FilterConfig;
}