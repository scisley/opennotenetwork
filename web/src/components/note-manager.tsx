"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RefreshCw, Trash2, Plus, Copy, Send, CheckCircle, Edit } from "lucide-react";
import {
  useNotes,
  useNoteWriters,
  useRunNoteWriter,
  useDeleteNote,
  useSubmitNote
} from "@/hooks/use-api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { NoteEditModal } from "./note-edit-modal";

interface NoteManagerProps {
  factCheckId: string;
  postUid: string;
}

export function NoteManager({ factCheckId }: NoteManagerProps) {
  const [selectedWriter, setSelectedWriter] = useState<string | null>(null);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  // Fetch data
  const { data: notesData, isLoading: notesLoading, refetch: refetchNotes } = useNotes(factCheckId);
  const { data: writersData, isLoading: writersLoading } = useNoteWriters();
  const runNoteWriter = useRunNoteWriter(factCheckId);
  const deleteNote = useDeleteNote(factCheckId);
  const submitNote = useSubmitNote();

  const notes = useMemo(() => notesData?.notes || [], [notesData]);
  const noteWriters = useMemo(() => writersData?.note_writers || [], [writersData]);

  // Reset selected writer when factCheckId changes (e.g., when cycling through fact checks)
  useEffect(() => {
    setSelectedWriter(null);
  }, [factCheckId]);

  // Auto-select first note writer if there are notes or if there's only one writer
  useEffect(() => {
    if (!selectedWriter) {
      // If there are existing notes, select the first one's writer
      if (notes.length > 0 && notes[0].note_writer?.slug) {
        setSelectedWriter(notes[0].note_writer.slug);
      }
      // Otherwise if there's only one note writer available, select it
      else if (noteWriters.length === 1) {
        setSelectedWriter(noteWriters[0].slug);
      }
    }
  }, [notes, noteWriters, selectedWriter]);
  
  // Get the note for the selected writer
  const selectedNote = notes.find(
    (note: any) => note.note_writer?.slug === selectedWriter
  );
  
  // Handle create/recreate note
  const handleRunNoteWriter = async (force: boolean = false) => {
    if (!selectedWriter) return;
    
    try {
      await runNoteWriter.mutateAsync({ 
        noteWriterSlug: selectedWriter, 
        force 
      });
      // Success - refetch notes
      refetchNotes();
    } catch (error) {
      console.error("Failed to run note writer:", error);
      alert("Failed to run note writer");
    }
  };
  
  // Handle delete
  const handleDelete = async () => {
    if (!selectedWriter) return;

    if (confirm("Are you sure you want to delete this note?")) {
      try {
        await deleteNote.mutateAsync(selectedWriter);
        // Success - refetch notes
        refetchNotes();
      } catch (error: any) {
        // Check if it's a 409 conflict error (note has submissions)
        if (error?.response?.status === 409) {
          alert("Cannot delete this note because it has already been submitted. Notes with submissions cannot be deleted to maintain submission history.");
        } else {
          // Generic error message for other errors
          const errorMessage = error?.response?.data?.detail || "Failed to delete note";
          alert(errorMessage);
        }
      }
    }
  };
  
  // Copy to clipboard
  const handleCopy = () => {
    if (selectedNote?.text) {
      navigator.clipboard.writeText(selectedNote.text);
      // Optional: Show some visual feedback that copy succeeded
    }
  };
  
  // Handle submit to X
  const handleSubmit = async () => {
    if (!selectedNote) return;
    
    try {
      await submitNote.mutateAsync(selectedNote.note_id);
      setShowSubmitDialog(false);
      refetchNotes();
    } catch (error: any) {
      setShowSubmitDialog(false);
      // Show user-friendly error message
      const errorMessage = error.response?.data?.detail || "Failed to submit note";
      console.error("Failed to submit note:", errorMessage);
      alert(errorMessage);
    }
  };
  
  if (notesLoading || writersLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Community Note Generation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-gray-500">Loading note writers...</p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle>Community Note Generation</CardTitle>
          <Badge variant="outline">
            {notes.length} note{notes.length !== 1 ? 's' : ''}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 flex-1 overflow-y-auto">
        {/* Note Writer Selection */}
        <div className="flex flex-col sm:flex-row gap-2">
          <Select value={selectedWriter || ""} onValueChange={setSelectedWriter}>
            <SelectTrigger className="flex-1 min-w-0">
              <SelectValue placeholder="Select a note writer" />
            </SelectTrigger>
            <SelectContent>
              {noteWriters.map((writer: any) => (
                <SelectItem key={writer.slug} value={writer.slug}>
                  {writer.name}
                  {writer.version && ` (v${writer.version})`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Action Buttons */}
          {selectedWriter && (
            <div className="flex gap-2 flex-shrink-0">
              {selectedNote ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRunNoteWriter(true)}
                    disabled={runNoteWriter.isPending}
                    className="flex-shrink-0"
                  >
                    <RefreshCw className="h-4 w-4 sm:mr-1" />
                    <span className="hidden sm:inline">Recreate</span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDelete}
                    disabled={deleteNote.isPending}
                    className="flex-shrink-0"
                  >
                    <Trash2 className="h-4 w-4 sm:mr-1" />
                    <span className="hidden sm:inline">Delete</span>
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRunNoteWriter(false)}
                  disabled={runNoteWriter.isPending}
                  className="flex-shrink-0"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Create Note
                </Button>
              )}
            </div>
          )}
        </div>
        
        {/* Note Display */}
        {selectedNote && (
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {selectedNote.submission && (
                  <Badge
                    variant={
                      selectedNote.submission.status === "displayed" ? "default" :
                      selectedNote.submission.status === "submitted" ? "secondary" :
                      selectedNote.submission.status === "not_displayed" ? "outline" :
                      "destructive"
                    }
                  >
                    {selectedNote.submission.status === "displayed" && <CheckCircle className="h-3 w-3 mr-1" />}
                    {selectedNote.submission.status}
                  </Badge>
                )}
                {selectedNote.is_edited && (
                  <Badge variant="secondary">Edited</Badge>
                )}
                {/* Evaluation Score */}
                {selectedNote.evaluation_json && (
                  <Badge
                    variant="outline"
                    className={
                      selectedNote.evaluation_json.error
                        ? "bg-red-50 border-red-300 text-red-800"
                        : selectedNote.evaluation_json.data?.claim_opinion_score !== undefined
                          ? selectedNote.evaluation_json.data.claim_opinion_score > -0.5
                            ? "bg-green-50 border-green-300 text-green-800"
                            : selectedNote.evaluation_json.data.claim_opinion_score < -1
                              ? "bg-red-50 border-red-300 text-red-800"
                              : "bg-yellow-50 border-yellow-300 text-yellow-800"
                          : "bg-gray-50 border-gray-300 text-gray-800"
                    }
                  >
                    {selectedNote.evaluation_json.error
                      ? "Evaluation Failed"
                      : selectedNote.evaluation_json.data?.claim_opinion_score !== undefined
                        ? `Score: ${selectedNote.evaluation_json.data.claim_opinion_score.toFixed(2)}`
                        : "Score: Unknown"
                    }
                  </Badge>
                )}
              </div>
              {selectedNote.status === "completed" && (
                <div className="flex gap-2 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="flex-shrink-0"
                  >
                    <Copy className="h-4 w-4 sm:mr-1" />
                    <span className="hidden sm:inline">Copy</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowEditModal(true)}
                    className="flex-shrink-0"
                  >
                    <Edit className="h-4 w-4 sm:mr-1" />
                    <span className="hidden sm:inline">Edit</span>
                  </Button>
                  {!selectedNote.submission && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowSubmitDialog(true)}
                      className="flex-shrink-0 whitespace-nowrap"
                    >
                      <Send className="h-4 w-4 sm:mr-1" />
                      <span className="hidden sm:inline">Submit to X</span>
                    </Button>
                  )}
                </div>
              )}
            </div>
            
            {selectedNote.status === "completed" && (
              <>
                {/* Note Text */}
                <div className={`${selectedNote.is_edited ? 'bg-blue-50 border-blue-200' : 'bg-amber-50 border-amber-200'} border rounded-lg p-4`}>
                  <p className="text-sm text-gray-900 leading-relaxed break-words">
                    {selectedNote.text}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    {selectedNote.text?.length || 0}/280 characters
                  </p>
                </div>

                {/* Links */}
                {selectedNote.links && selectedNote.links.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-gray-600">Links:</p>
                    {selectedNote.links.map((link: any, idx: number) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-xs text-blue-600 hover:underline break-all"
                      >
                        {link.url}
                      </a>
                    ))}
                  </div>
                )}
                
                {/* Submission JSON Preview */}
                {selectedNote.submission_json && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                      View Submission JSON
                    </summary>
                    <pre className="mt-2 p-2 bg-gray-50 rounded overflow-x-auto">
                      {JSON.stringify(selectedNote.submission_json, null, 2)}
                    </pre>
                  </details>
                )}
                
                {/* Submission Details */}
                {selectedNote.submission && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium text-gray-600">Submission Details</p>
                      {selectedNote.submission.test_mode && (
                        <Badge variant="outline" className="text-xs">Test Mode</Badge>
                      )}
                    </div>
                    <div className="space-y-1 text-xs text-gray-600">
                      <p>Submitted: {new Date(selectedNote.submission.submitted_at).toLocaleString()}</p>
                      {selectedNote.submission.x_note_id && (
                        <p>X Note ID: {selectedNote.submission.x_note_id}</p>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
            
            {selectedNote.status === "failed" && selectedNote.error_message && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">
                  Error: {selectedNote.error_message}
                </p>
              </div>
            )}
          </div>
        )}
        
        {/* Empty State */}
        {selectedWriter && !selectedNote && (
          <div className="text-center py-6 bg-gray-50 rounded-lg">
            <p className="text-gray-600">
              No note generated with this writer yet.
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Click &quot;Create Note&quot; to generate one.
            </p>
          </div>
        )}
        
        {!selectedWriter && (
          <div className="text-center py-6 bg-gray-50 rounded-lg">
            <p className="text-gray-600">
              Select a note writer to view or generate notes.
            </p>
          </div>
        )}
      </CardContent>

      {/* Edit Modal */}
      {selectedNote && (
        <NoteEditModal
          open={showEditModal}
          onClose={() => setShowEditModal(false)}
          note={selectedNote}
          onSuccess={() => {
            refetchNotes();
            setShowEditModal(false);
          }}
        />
      )}

      {/* Submit Dialog */}
      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit to Community Notes?</DialogTitle>
            <DialogDescription>
              This will submit the note to X.com Community Notes in test mode.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitNote.isPending}>
              {submitNote.isPending ? "Submitting..." : "Submit"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}