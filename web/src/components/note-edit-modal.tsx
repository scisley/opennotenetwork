"use client";

import { useState, useEffect } from "react";
import { Plus, X, ChevronDown } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useEditNote } from "@/hooks/use-api";
import { countTwitterCharacters, getRemainingCharacters } from "@/lib/twitter-utils";
import { AlertCircle } from "lucide-react";

interface NoteEditModalProps {
  open: boolean;
  onClose: () => void;
  note: {
    note_id: string;
    text: string;
    original_text?: string;
    original_links?: Array<{url: string}>;
    links?: Array<{url: string}>;
    is_edited?: boolean;
  };
  onSuccess?: () => void;
}

export function NoteEditModal({ open, onClose, note, onSuccess }: NoteEditModalProps) {
  const [text, setText] = useState(note.text);
  const [links, setLinks] = useState<Array<{url: string}>>(note.links || []);
  const [newLinkUrl, setNewLinkUrl] = useState("");
  const editNote = useEditNote();

  // Calculate character count including links (each link counts as 1 character)
  const fullText = links.length > 0
    ? `${text} ${links.map(l => l.url).join(' ')}`
    : text;
  const remainingChars = getRemainingCharacters(fullText);
  const isOverLimit = remainingChars < 0;

  // Simple URL validation
  const isValidUrl = (url: string): boolean => {
    if (!url || url.trim() === '') return true; // Empty is valid (user might be typing)
    try {
      const urlObj = new URL(url);
      return ['http:', 'https:'].includes(urlObj.protocol);
    } catch {
      return false;
    }
  };

  // Check if any links are invalid
  const hasInvalidLinks = links.some(link => !isValidUrl(link.url));
  const canSave = !isOverLimit && !hasInvalidLinks && !editNote.isPending;

  // Reset text and links when note changes
  useEffect(() => {
    setText(note.text);
    setLinks(note.links || []);
  }, [note.text, note.links]);

  const handleSave = async () => {
    if (isOverLimit) return;

    try {
      await editNote.mutateAsync({
        noteId: note.note_id,
        text,
        links: links.length > 0 ? links : undefined
      });

      onSuccess?.();
      onClose();
    } catch (error) {
      console.error("Failed to edit note:", error);
    }
  };

  const handleAddLink = () => {
    const trimmedUrl = newLinkUrl.trim();
    if (trimmedUrl) {
      setLinks([...links, { url: trimmedUrl }]);
      setNewLinkUrl("");
    }
  };

  const handleRemoveLink = (index: number) => {
    setLinks(links.filter((_, i) => i !== index));
  };

  const handleEditLink = (index: number, newUrl: string) => {
    const updatedLinks = [...links];
    updatedLinks[index] = { url: newUrl };
    setLinks(updatedLinks);
  };

  const handleCancel = () => {
    setText(note.text); // Reset to original
    setLinks(note.links || []); // Reset links
    setNewLinkUrl(""); // Clear new link input
    onClose();
  };

  // Only show original text section if the note has been edited before
  const showOriginal = note.is_edited && note.original_text;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Community Note</DialogTitle>
          <DialogDescription>
            Modify the note text before submitting to X. URLs count as 1 character each.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Original Text (Read-only) - Only show if note was previously edited */}
          {showOriginal && (
            <Collapsible className="space-y-2">
              <CollapsibleTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="flex items-center justify-between w-full p-2 hover:bg-gray-50"
                >
                  <span className="text-sm text-gray-600">View Original AI-Generated Text</span>
                  <ChevronDown className="h-4 w-4 text-gray-400 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mt-2">
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {note.original_text}
                    {note.original_links && note.original_links.length > 0 && (
                      <>
                        {"\n\n"}
                        {note.original_links.map((link: {url: string}) => link.url).join("\n")}
                      </>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    {(() => {
                      const fullOriginalText = note.original_text +
                        (note.original_links && note.original_links.length > 0
                          ? "\n\n" + note.original_links.map((link: {url: string}) => link.url).join("\n")
                          : "");
                      return countTwitterCharacters(fullOriginalText);
                    })()} characters
                  </p>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Editable Text */}
          <div className="space-y-2">
            <Label htmlFor="note-text">Note Text</Label>
            <textarea
              id="note-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              className={`w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ${isOverLimit ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}`}
              placeholder="Enter your community note text..."
            />
          </div>

          {/* Editable Links Section */}
          <div className="space-y-2">
            <Label className="text-sm text-gray-600">Links</Label>
            <div className="space-y-2">
              {links.map((link, idx) => {
                const isInvalid = !isValidUrl(link.url);
                return (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="url"
                      value={link.url}
                      onChange={(e) => handleEditLink(idx, e.target.value)}
                      className={`flex-1 rounded-md border px-2 py-1 text-sm focus:outline-none focus:ring-1 ${
                        isInvalid
                          ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                      }`}
                      placeholder="https://example.com"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveLink(idx)}
                      className="p-1 h-7 w-7"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                );
              })}

              {/* Add new link */}
              <div className="flex items-center gap-2">
                <input
                  type="url"
                  value={newLinkUrl}
                  onChange={(e) => setNewLinkUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddLink())}
                  className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Add new link..."
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddLink}
                  className="p-1 h-7 w-7"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Character Count and Validation Status */}
          <div className="pt-2 border-t space-y-2">
            {hasInvalidLinks && (
              <div className="text-sm text-red-600">
                <AlertCircle className="inline h-4 w-4 mr-1" />
                Please fix invalid URLs (must start with http:// or https://)
              </div>
            )}
            <div className={`text-sm ${isOverLimit ? 'text-red-600' : 'text-gray-600'}`}>
              {isOverLimit && <AlertCircle className="inline h-4 w-4 mr-1" />}
              <span className="font-medium">Total: {countTwitterCharacters(fullText)}/280 characters</span>
              {remainingChars !== 0 && (
                <span className="ml-2">
                  ({remainingChars > 0 ? `${remainingChars} remaining` : `${Math.abs(remainingChars)} over`})
                </span>
              )}
              {links.length > 0 && (
                <span className="block text-xs mt-1 text-gray-500">
                  Note text: {countTwitterCharacters(text)} chars + {links.length} link{links.length !== 1 ? 's' : ''} ({links.length} char{links.length !== 1 ? 's' : ''})
                </span>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={editNote.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!canSave}
          >
            {editNote.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}