'use client';

import { SingleSelectFilter } from './single-select-filter';
import { Classifier } from '@/types/api';

export type NoteStatus = 'not_submitted' | 'submitted' | 'rated_helpful' | 'rated_unhelpful' | 'needs_more_ratings';

interface NoteStatusFilterProps {
  value?: NoteStatus;
  onChange: (value?: NoteStatus) => void;
}

export function NoteStatusFilter({ value, onChange }: NoteStatusFilterProps) {
  // Create a virtual classifier that matches the backend structure
  const virtualClassifier: Classifier = {
    classifier_id: 'virtual-note-status',
    slug: 'note-status',
    display_name: 'Note Status',
    description: 'Filter posts by their Community Note status',
    group_name: 'processing-status',
    is_active: true,
    output_schema: {
      type: 'single',
      choices: [
        'not_submitted',
        'submitted',
        'rated_helpful',
        'rated_unhelpful',
        'needs_more_ratings'
      ],
      choice_labels: {
        'not_submitted': 'Not submitted',
        'submitted': 'Submitted',
        'rated_helpful': 'Rated Helpful',
        'rated_unhelpful': 'Rated Unhelpful',
        'needs_more_ratings': 'Needs more ratings'
      }
    },
    config: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  return (
    <SingleSelectFilter
      classifier={virtualClassifier}
      currentValue={value}
      hasClassification={false}
      onValueChange={(val) => onChange(val as NoteStatus | undefined)}
      onHasClassificationChange={() => {}}
      hideHasClassification={true}
    />
  );
}
