"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, FileText, Clock, XCircle } from "lucide-react";
import { useNotes } from "@/hooks/use-api";
import { TrackedLink } from "@/components/tracked-link";

interface CommunityNoteProps {
  factCheckId: string | null | undefined;  // undefined = still loading
  submissionStatus?: string | null;
}

export function CommunityNote({ factCheckId, submissionStatus }: CommunityNoteProps) {
  const { data: notesData, isLoading } = useNotes(factCheckId || "");

  // Get the first completed note
  const notes = notesData?.notes || [];
  const completedNote = notes.find((note: any) => note.status === "completed");
  const note = completedNote || notes[0];

  // Show loading state if factCheckId is undefined (still determining) OR actively loading notes
  if (factCheckId === undefined || (factCheckId && isLoading)) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Proposed Community Note
            {submissionStatus === "displayed" && (
              <Badge variant="default" className="ml-auto text-xs bg-green-600 hover:bg-green-700">
                Rated Helpful
              </Badge>
            )}
            {submissionStatus === "not_displayed" && (
              <Badge variant="default" className="ml-auto text-xs bg-red-600 hover:bg-red-700">
                Rated Unhelpful
              </Badge>
            )}
            {submissionStatus === "submitted" && (
              <Badge variant="secondary" className="ml-auto text-xs">
                Needs more ratings
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // If factCheckId is explicitly null (not undefined), no fact check exists
  if (factCheckId === null) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Proposed Community Note
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">No fact check available</p>
            <p className="text-sm text-gray-500 mt-2">
              This post was not selected for fact-checking
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Only show "no note" message after loading is complete and we confirm there's no note
  if (!note) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Proposed Community Note
            {submissionStatus && (
              <Badge
                variant={submissionStatus === "accepted" ? "default" : "outline"}
                className="ml-auto text-xs"
              >
                {submissionStatus === "accepted" ? "Accepted" : "Submitted"}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">No Community Note generated</p>
            <p className="text-sm text-gray-500 mt-2">
              The fact-check did not produce a note
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }


  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Proposed Community Note
          {submissionStatus === "displayed" && (
            <Badge variant="default" className="ml-auto text-xs bg-green-600 hover:bg-green-700">
              Rated Helpful
            </Badge>
          )}
          {submissionStatus === "not_displayed" && (
            <Badge variant="default" className="ml-auto text-xs bg-red-600 hover:bg-red-700">
              Rated Unhelpful
            </Badge>
          )}
          {submissionStatus === "submitted" && (
            <Badge variant="secondary" className="ml-auto text-xs">
              Needs more ratings
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {note.status === "completed" ? (
          <div className="space-y-4">
            {/* Note Text */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {note.text}
              </p>
            </div>

            {/* Links */}
            {note.links && note.links.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                  Links
                </p>
                <div className="space-y-1">
                  {note.links.map((link: any, index: number) => (
                    <TrackedLink
                      key={index}
                      href={link.url || link}
                      context="note"
                      className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="truncate">
                        {link.url || link}
                      </span>
                    </TrackedLink>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : note.status === "failed" ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-900">Generation Failed</p>
                {note.error_message && (
                  <p className="text-sm text-red-700 mt-1">{note.error_message}</p>
                )}
              </div>
            </div>
          </div>
        ) : note.status === "processing" ? (
          <div className="text-center py-8">
            <Clock className="h-12 w-12 text-blue-500 mx-auto mb-3 animate-pulse" />
            <p className="text-gray-600">Generating Proposed Community Note...</p>
            <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">Note generation pending</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}