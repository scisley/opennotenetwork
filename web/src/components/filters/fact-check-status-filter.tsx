'use client';

import { SingleSelectFilter } from './single-select-filter';
import { Classifier } from '@/types/api';

export type FactCheckStatus = 'no_fact_check' | 'fact_checked' | 'note_written' | 'note_submitted';

interface FactCheckStatusFilterProps {
  value?: FactCheckStatus;
  onChange: (value?: FactCheckStatus) => void;
}

export function FactCheckStatusFilter({ value, onChange }: FactCheckStatusFilterProps) {
  // Create a virtual classifier that matches the backend structure
  const virtualClassifier: Classifier = {
    classifier_id: 'virtual-fact-check-status',
    slug: 'fact-check-status',
    display_name: 'Fact Check Status',
    description: 'Filter posts by their fact-checking progress',
    group_name: 'processing-status',
    is_active: true,
    output_schema: {
      type: 'single',
      choices: [
        'no_fact_check',
        'fact_checked',
        'note_written',
        'note_submitted'
      ],
      choice_labels: {
        'no_fact_check': 'No fact check',
        'fact_checked': 'Fact checked',
        'note_written': 'Note written',
        'note_submitted': 'Note submitted'
      }
    },
    config: null,  // Add missing config field
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  return (
    <SingleSelectFilter
      classifier={virtualClassifier}
      currentValue={value}
      hasClassification={false}  // We don't need the "Has classification" checkbox for this
      onValueChange={(val) => onChange(val as FactCheckStatus | undefined)}
      onHasClassificationChange={() => {}}  // No-op since we don't use this
      hideHasClassification={true}  // Add this prop to hide the checkbox
    />
  );
}