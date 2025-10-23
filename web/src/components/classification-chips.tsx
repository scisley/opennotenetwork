'use client';

import { useState } from 'react';
import { Classification } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Modal, ModalHeader, ModalContent } from '@/components/ui/modal';
import { Info } from 'lucide-react';

interface ClassificationChipsProps {
  classifications: Classification[];
}

export function ClassificationChips({ classifications }: ClassificationChipsProps) {
  const [selectedClassification, setSelectedClassification] = useState<Classification | null>(null);

  if (!classifications || classifications.length === 0) {
    return null;
  }

  const getClassificationValue = (clf: Classification) => {
    const data = clf.classification_data;
    
    if (data.type === 'single' && data.value) {
      const choice = clf.output_schema.choices?.find((c: any) => c.value === data.value);
      return {
        label: choice?.label || data.value,
        confidence: data.confidence,
        color: choice?.color
      };
    }
    
    if (data.type === 'multi' && data.values && data.values.length > 0) {
      const firstValue = data.values[0];
      const choice = clf.output_schema.choices?.find((c: any) => c.value === firstValue.value);
      const more = data.values.length > 1 ? ` +${data.values.length - 1}` : '';
      return {
        label: (choice?.label || firstValue.value) + more,
        confidence: firstValue.confidence,
        color: choice?.color
      };
    }
    
    if (data.type === 'hierarchical' && data.levels && data.levels.length > 0) {
      const lastLevel = data.levels[data.levels.length - 1];
      return {
        label: lastLevel.value,
        confidence: lastLevel.confidence,
        color: undefined
      };
    }
    
    return { label: 'Unknown', confidence: undefined, color: undefined };
  };

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        {classifications.map((clf) => {
          const value = getClassificationValue(clf);
          return (
            <button
              key={clf.classifier_slug}
              onClick={() => setSelectedClassification(clf)}
              className="group flex flex-col px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm transition-colors h-[60px] relative"
              style={{
                backgroundColor: value.color ? `${value.color}15` : undefined,
                borderColor: value.color ? value.color : undefined,
                borderWidth: value.color ? '1px' : undefined,
                borderStyle: value.color ? 'solid' : undefined
              }}
            >
              <div className="font-medium text-gray-700 truncate w-full text-left">
                {clf.classifier_display_name}
              </div>
              <div className="flex items-center justify-between w-full mt-1">
                <span className="text-gray-900 truncate flex-1 text-left">
                  {value.label}
                </span>
                {value.confidence !== undefined && (
                  <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                    {Math.round(value.confidence * 100)}%
                  </span>
                )}
              </div>
              <Info className="absolute top-2 right-2 w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          );
        })}
      </div>

      <Modal
        isOpen={!!selectedClassification}
        onClose={() => setSelectedClassification(null)}
      >
        {selectedClassification && (
          <>
            <ModalHeader>
              <h2 className="text-xl font-semibold">
                {selectedClassification.classifier_display_name}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Classification Details
              </p>
            </ModalHeader>
            <ModalContent>
              <div className="space-y-4">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-600">Classifier Slug:</span>
                    <p className="text-gray-900 font-mono">{selectedClassification.classifier_slug}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Group:</span>
                    <p className="text-gray-900">{selectedClassification.classifier_group || 'None'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Type:</span>
                    <p className="text-gray-900">{selectedClassification.classification_type}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Created:</span>
                    <p className="text-gray-900">
                      {new Date(selectedClassification.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Updated:</span>
                    <p className="text-gray-900">
                      {new Date(selectedClassification.updated_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Classification Result */}
                <div>
                  <h3 className="font-medium text-gray-600 mb-2">Classification Result</h3>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <ClassificationResultDetail classification={selectedClassification} />
                  </div>
                </div>

                {/* Raw Data */}
                <div>
                  <h3 className="font-medium text-gray-600 mb-2">Raw Classification Data</h3>
                  <div className="bg-gray-900 rounded-lg p-3 overflow-auto max-h-48">
                    <pre className="text-green-400 text-xs font-mono">
                      {JSON.stringify(selectedClassification.classification_data, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Output Schema */}
                <div>
                  <h3 className="font-medium text-gray-600 mb-2">Output Schema</h3>
                  <div className="bg-gray-900 rounded-lg p-3 overflow-auto max-h-48">
                    <pre className="text-green-400 text-xs font-mono">
                      {JSON.stringify(selectedClassification.output_schema, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </ModalContent>
          </>
        )}
      </Modal>
    </>
  );
}

function ClassificationResultDetail({ classification }: { classification: Classification }) {
  const data = classification.classification_data;
  const schema = classification.output_schema;

  // Single choice
  if (data.type === 'single' && data.value) {
    const choice = schema.choices?.find((c: any) => c.value === data.value);
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge 
            style={{ 
              backgroundColor: choice?.color ? `${choice.color}20` : undefined,
              borderColor: choice?.color,
              color: choice?.color 
            }}
            variant="outline"
            className="text-sm"
          >
            {choice?.label || data.value}
          </Badge>
          {data.confidence && (
            <span className="text-sm text-gray-600">
              Confidence: {(data.confidence * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>
    );
  }

  // Multi choice
  if (data.type === 'multi' && data.values) {
    return (
      <div className="space-y-2">
        {data.values.map((item, idx) => {
          const choice = schema.choices?.find((c: any) => c.value === item.value);
          return (
            <div key={idx} className="flex items-center gap-2">
              <Badge variant="secondary" className="text-sm">
                {choice?.label || item.value}
              </Badge>
              {item.confidence && (
                <span className="text-xs text-gray-600">
                  {(item.confidence * 100).toFixed(1)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Hierarchical
  if (data.type === 'hierarchical' && data.levels) {
    return (
      <div className="flex items-center gap-2">
        {data.levels.map((level, idx) => {
          const levelSchema = schema.levels?.[idx];
          const choice = levelSchema?.choices?.find((c: any) => c.value === level.value) ||
                        levelSchema?.choices_by_parent?.[data.levels![idx-1]?.value]?.find((c: any) => c.value === level.value);
          
          return (
            <div key={idx} className="flex items-center">
              {idx > 0 && <span className="mx-2 text-gray-400">→</span>}
              <Badge variant="outline" className="text-sm">
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