'use client';

import { Badge } from '@/components/ui/badge';

interface ClassificationData {
  classifier_slug: string;
  classifier_display_name: string;
  classification_data: any;
  output_schema?: any;
}

interface ClassificationChipRowProps {
  classifications: ClassificationData[];
  className?: string;
}

export function ClassificationChipRow({ classifications, className = '' }: ClassificationChipRowProps) {
  if (!classifications || classifications.length === 0) {
    return null;
  }

  const getClassificationLabel = (clf: ClassificationData) => {
    const data = clf.classification_data;
    
    // Single choice
    if (data.type === 'single' && data.value) {
      return data.value;
    }
    
    // Multi choice - show first value with count
    if (data.type === 'multi' && data.values && data.values.length > 0) {
      const firstValue = typeof data.values[0] === 'object' ? data.values[0].value : data.values[0];
      const more = data.values.length > 1 ? ` +${data.values.length - 1}` : '';
      return firstValue + more;
    }
    
    // Hierarchical - show last level
    if (data.type === 'hierarchical' && data.hierarchy) {
      return data.hierarchy.level2 || data.hierarchy.level1 || 'Unknown';
    }
    
    // Alternative hierarchical format
    if (data.type === 'hierarchical' && data.levels && data.levels.length > 0) {
      const lastLevel = data.levels[data.levels.length - 1];
      return typeof lastLevel === 'object' ? lastLevel.value : lastLevel;
    }
    
    return 'Unknown';
  };

  const getClassificationColor = (clf: ClassificationData) => {
    const data = clf.classification_data;
    
    // Map common classification values to colors
    if (data.value === 'not_climate_related') return 'bg-gray-100 text-gray-700';
    if (data.value === 'climate_related') return 'bg-green-100 text-green-700';
    if (data.value === 'misleading') return 'bg-red-100 text-red-700';
    if (data.value === 'accurate') return 'bg-blue-100 text-blue-700';
    
    // Default color scheme based on classifier type
    if (clf.classifier_slug.includes('climate')) return 'bg-emerald-100 text-emerald-700';
    if (clf.classifier_slug.includes('fact')) return 'bg-amber-100 text-amber-700';
    if (clf.classifier_slug.includes('topic')) return 'bg-purple-100 text-purple-700';
    if (clf.classifier_slug.includes('science')) return 'bg-cyan-100 text-cyan-700';
    
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {classifications.map((clf) => {
        const label = getClassificationLabel(clf);
        const colorClass = getClassificationColor(clf);
        
        return (
          <Badge
            key={clf.classifier_slug}
            variant="secondary"
            className={`text-xs ${colorClass}`}
            title={`${clf.classifier_display_name}: ${label}`}
          >
            <span className="font-medium mr-1">
              {clf.classifier_display_name.split(' ')[0]}:
            </span>
            {label}
          </Badge>
        );
      })}
    </div>
  );
}