'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface RawJsonViewerProps {
  data: any;
  title?: string;
}

export function RawJsonViewer({ data, title = 'Raw JSON Data' }: RawJsonViewerProps) {
  const [showData, setShowData] = useState(false);

  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle
          className="flex items-center justify-between cursor-pointer hover:text-gray-600"
          onClick={() => setShowData(!showData)}
        >
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {showData ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </CardTitle>
      </CardHeader>
      {showData && (
        <CardContent>
          <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-[48rem]">
            <pre className="text-green-400 text-xs font-mono whitespace-pre-wrap">
              {data ? JSON.stringify(data, null, 2) : 'No data available'}
            </pre>
          </div>
        </CardContent>
      )}
    </Card>
  );
}