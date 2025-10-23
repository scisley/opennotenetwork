'use client';

import { Classification } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ClassificationDisplayProps {
  classifications: Classification[];
}

export function ClassificationDisplay({ classifications }: ClassificationDisplayProps) {
  if (!classifications || classifications.length === 0) {
    return null;
  }

  // Group classifications by group
  const grouped = classifications.reduce((acc, clf) => {
    const group = clf.classifier_group || 'Other';
    if (!acc[group]) acc[group] = [];
    acc[group].push(clf);
    return acc;
  }, {} as Record<string, Classification[]>);

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([group, items]) => (
        <Card key={group}>
          <CardHeader>
            <CardTitle className="text-lg">{group}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {items.map((clf) => (
              <div key={clf.classifier_slug} className="border-l-4 border-l-blue-500 pl-4">
                <div className="font-medium text-sm text-gray-700 mb-1">
                  {clf.classifier_display_name}
                </div>
                <ClassificationResult classification={clf} />
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ClassificationResult({ classification }: { classification: Classification }) {
  const data = classification.classification_data;
  const schema = classification.output_schema;

  // Single choice classification
  if (data.type === 'single' && data.value) {
    const choice = schema.choices?.find((c: any) => c.value === data.value);
    return (
      <div className="flex items-center gap-2">
        <Badge 
          style={{ 
            backgroundColor: choice?.color ? `${choice.color}20` : undefined,
            borderColor: choice?.color,
            color: choice?.color 
          }}
          variant="outline"
        >
          {choice?.label || data.value}
        </Badge>
        {data.confidence && (
          <span className="text-xs text-gray-500">
            {(data.confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>
    );
  }

  // Multi choice classification
  if (data.type === 'multi' && data.values) {
    return (
      <div className="flex flex-wrap gap-2">
        {data.values.map((item, idx) => {
          const choice = schema.choices?.find((c: any) => c.value === item.value);
          return (
            <Badge 
              key={idx}
              variant="secondary"
              className="text-xs"
            >
              {choice?.icon} {choice?.label || item.value}
              {item.confidence && (
                <span className="ml-1 opacity-60">
                  ({(item.confidence * 100).toFixed(0)}%)
                </span>
              )}
            </Badge>
          );
        })}
      </div>
    );
  }

  // Hierarchical classification
  if (data.type === 'hierarchical' && data.levels) {
    return (
      <div className="flex items-center gap-1">
        {data.levels.map((level, idx) => {
          const levelSchema = schema.levels?.[idx];
          const choice = levelSchema?.choices?.find((c: any) => c.value === level.value) ||
                        levelSchema?.choices_by_parent?.[data.levels![idx-1]?.value]?.find((c: any) => c.value === level.value);
          
          return (
            <div key={idx} className="flex items-center">
              {idx > 0 && <span className="mx-1 text-gray-400">→</span>}
              <Badge variant="outline" className="text-xs">
                {choice?.label || level.value}
                {level.confidence && (
                  <span className="ml-1 opacity-60">
                    ({(level.confidence * 100).toFixed(0)}%)
                  </span>
                )}
              </Badge>
            </div>
          );
        })}
      </div>
    );
  }

  // Fallback
  return (
    <div className="text-sm text-gray-600">
      <pre className="text-xs">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}