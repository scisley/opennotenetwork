"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSubmissionQueue } from "@/hooks/use-api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronLeft, ChevronRight, ListTodo } from "lucide-react";

const STORAGE_KEY = "submission-queue-min-score";
const DEFAULT_MIN_SCORE = -0.5;

export default function SubmissionQueuePage() {
  const [appliedMinScore, setAppliedMinScore] = useState<number>(DEFAULT_MIN_SCORE);
  const [inputMinScore, setInputMinScore] = useState<string>(DEFAULT_MIN_SCORE.toString());
  const [page, setPage] = useState(0);
  const limit = 25;

  // Load min score from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const value = parseFloat(saved);
      setAppliedMinScore(value);
      setInputMinScore(saved);
    }
  }, []);

  // Save applied min score to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, appliedMinScore.toString());
  }, [appliedMinScore]);

  const { data, isLoading, error } = useSubmissionQueue({
    min_score: appliedMinScore,
    limit,
    offset: page * limit,
  });

  const totalPages = Math.ceil((data?.total || 0) / limit);

  const getScoreBadgeColor = (score: number) => {
    if (score > -0.5) {
      return "bg-green-50 border-green-300 text-green-800";
    } else if (score > -1) {
      return "bg-yellow-50 border-yellow-300 text-yellow-800";
    } else {
      return "bg-red-50 border-red-300 text-red-800";
    }
  };

  const handleApplyFilter = () => {
    const parsed = parseFloat(inputMinScore);
    if (!isNaN(parsed)) {
      setAppliedMinScore(parsed);
      setPage(0); // Reset to first page when filter changes
    }
  };

  if (isLoading && !data) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500">Loading submission queue...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-800">Failed to load submission queue</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <ListTodo className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Submission Queue</h1>
          <p className="text-gray-600 mt-1">
            Posts with notes ready for submission to X.com Community Notes
          </p>
        </div>
      </div>

      {/* Summary Card */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-xl">Queue Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 bg-white rounded-lg">
              <span className="text-gray-700 font-medium">Posts in Queue</span>
              <Badge variant="secondary" className="text-xl px-4 py-1">
                {data?.total || 0}
              </Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-white rounded-lg">
              <span className="text-gray-700 font-medium">
                Minimum Score Threshold
              </span>
              <Badge variant="outline" className="text-xl px-4 py-1">
                {appliedMinScore.toFixed(2)}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filter Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Settings</CardTitle>
          <CardDescription>
            Adjust the minimum claim_opinion_score threshold
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-4">
            <div className="flex-1 max-w-xs">
              <Label htmlFor="min-score">Minimum Score</Label>
              <Input
                id="min-score"
                type="number"
                step="0.1"
                value={inputMinScore}
                onChange={(e) => setInputMinScore(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleApplyFilter();
                  }
                }}
                className="mt-1"
              />
              <div className="flex gap-2 mt-1">
                <Button
                  size="sm"
                  onClick={handleApplyFilter}
                >
                  Apply Filter
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setInputMinScore(DEFAULT_MIN_SCORE.toString());
                    setAppliedMinScore(DEFAULT_MIN_SCORE);
                    setPage(0);
                  }}
                >
                  Reset to Default
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Posts Ready for Submission</CardTitle>
          <CardDescription>
            Click the Manage button to open the post management page
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border rounded-lg overflow-x-auto">
            <Table className="min-w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[120px]">Best Score</TableHead>
                  <TableHead className="w-[100px]">Notes</TableHead>
                  <TableHead className="min-w-[400px]">Post Text</TableHead>
                  <TableHead className="w-[120px]">Date</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items?.map((item: any) => (
                  <TableRow key={item.post_uid}>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={getScoreBadgeColor(item.best_score)}
                      >
                        {item.best_score.toFixed(2)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{item.note_count}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[500px]">
                      <p className="text-sm line-clamp-2 break-words">
                        {item.post_text}
                      </p>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {new Date(item.created_at).toLocaleString(undefined, {
                        month: 'numeric',
                        day: 'numeric',
                        year: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                      })}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/posts/${item.post_uid}/manage`}
                        className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all h-8 px-3 hover:bg-accent hover:text-accent-foreground"
                      >
                        Manage
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {data?.items?.length === 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500">
                No posts found matching the score threshold
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Try lowering the minimum score to see more results
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {page * limit + 1} to{" "}
                {Math.min((page + 1) * limit, data?.total || 0)} of{" "}
                {data?.total || 0}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages - 1}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
