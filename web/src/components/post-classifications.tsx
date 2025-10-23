'use client';

import { ClassificationAdmin } from '@/components/classification-admin';

interface PostClassificationsProps {
  postUid: string;
}

export function PostClassifications({ postUid }: PostClassificationsProps) {
  return (
    <ClassificationAdmin
      postUid={postUid}
      onClassified={() => {
        // The mutation in ClassificationAdmin already invalidates the query
        // This is just for any additional actions we might want
      }}
    />
  );
}