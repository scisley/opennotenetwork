'use client';

import { useHealthCheck, usePublicNotes } from '@/hooks/use-api';
import { Badge } from '@/components/ui/badge';

export function ApiStatus() {
  const { data: healthData, isLoading: healthLoading, error: healthError } = useHealthCheck();
  const { data: notesData, isLoading: notesLoading, error: notesError } = usePublicNotes();

  const getStatusBadge = (loading: boolean, error: any, data: any) => {
    if (loading) return <Badge variant="outline">Loading...</Badge>;
    if (error) return <Badge variant="destructive">Error</Badge>;
    if (data) return <Badge variant="default">Connected</Badge>;
    return <Badge variant="secondary">Unknown</Badge>;
  };

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span>API Health</span>
        {getStatusBadge(healthLoading, healthError, healthData)}
      </div>
      <div className="flex justify-between">
        <span>Public Notes</span>
        {getStatusBadge(notesLoading, notesError, notesData)}
      </div>
      {notesData && (
        <div className="flex justify-between">
          <span>Total Notes</span>
          <Badge variant="outline">{notesData.total}</Badge>
        </div>
      )}
      {(healthError || notesError) && (
        <div className="text-xs text-red-600 mt-2">
          Backend connection failed. Make sure the API server is running on localhost:8000
        </div>
      )}
    </div>
  );
}