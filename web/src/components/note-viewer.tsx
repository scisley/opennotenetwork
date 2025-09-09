"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { InfoIcon } from "lucide-react";

interface NoteViewerProps {
  conciseBody?: string | null;
  submissionStatus?: string | null;
  hasNote?: boolean;
}

export function NoteViewer({ conciseBody, submissionStatus, hasNote }: NoteViewerProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Community Note</CardTitle>
          {hasNote && submissionStatus && (
            <Badge
              variant={
                submissionStatus === "accepted"
                  ? "default"
                  : submissionStatus === "submitted"
                  ? "secondary"
                  : "outline"
              }
            >
              {submissionStatus === "accepted"
                ? "Accepted"
                : submissionStatus === "submitted"
                ? "Submitted"
                : submissionStatus}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {conciseBody ? (
          <div className="space-y-3">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-gray-900 leading-relaxed">
                {conciseBody}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {conciseBody.length}/280 characters
              </p>
            </div>
            {submissionStatus === "accepted" && (
              <div className="flex items-start gap-2 text-xs text-green-700">
                <InfoIcon className="h-3 w-3 mt-0.5" />
                <p>This note has been accepted and is visible on X.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="flex flex-col items-center gap-3">
              <div className="p-3 bg-gray-100 rounded-full">
                <InfoIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="space-y-1">
                <p className="text-gray-600 font-medium">
                  No Community Note Available
                </p>
                <p className="text-sm text-gray-500 max-w-xs mx-auto">
                  A community note has not been generated for this post yet.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}