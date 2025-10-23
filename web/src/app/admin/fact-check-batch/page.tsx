"use client";

import { useState, useEffect } from "react";
import { SimpleDateRangePicker } from "@/components/ui/simple-date-range-picker";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { useFactCheckers } from "@/hooks/use-api";
import { useAuthenticatedApi } from "@/lib/auth-axios";
import { AlertCircle, Loader2, CheckCircle, XCircle } from "lucide-react";

interface JobStatus {
  job_id: string;
  total_posts: number;
  processed: number;
  fact_checks_triggered: number;
  skipped: number;
  errors: string[];
  status: "running" | "completed" | "failed";
  progress_percentage: number;
  started_at: string;
  completed_at?: string;
}

interface DateRangeState {
  startDate: Date | undefined;
  endDate: Date | undefined;
  postCount: number | null;
  isCountingPosts: boolean;
}

interface JobState {
  currentJob: JobStatus | null;
  isRunning: boolean;
}

export default function FactCheckBatchPage() {
  const [dateRange, setDateRange] = useState<DateRangeState>({
    startDate: undefined,
    endDate: undefined,
    postCount: null,
    isCountingPosts: false,
  });
  const [jobState, setJobState] = useState<JobState>({
    currentJob: null,
    isRunning: false,
  });
  const [selectedFactCheckers, setSelectedFactCheckers] = useState<string[]>(
    []
  );
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: factCheckersData, isLoading: isLoadingFactCheckers } =
    useFactCheckers();
  const authApi = useAuthenticatedApi();

  // Fetch post count when dates or fact checkers change
  useEffect(() => {
    if (dateRange.startDate && dateRange.endDate) {
      fetchPostCount();
    } else {
      setDateRange((prev) => ({ ...prev, postCount: null }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange.startDate, dateRange.endDate, selectedFactCheckers]);

  // Poll job status when running
  useEffect(() => {
    if (jobState.currentJob && jobState.currentJob.status === "running") {
      const interval = setInterval(fetchJobStatus, 4000); // Poll every 4 seconds
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobState.currentJob]);

  const fetchPostCount = async () => {
    if (!dateRange.startDate || !dateRange.endDate) return;

    setDateRange((prev) => ({ ...prev, isCountingPosts: true }));
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append("start_date", dateRange.startDate.toISOString());
      params.append("end_date", dateRange.endDate.toISOString());

      // Add selected fact checkers
      if (selectedFactCheckers.length > 0) {
        selectedFactCheckers.forEach((slug) => {
          params.append("fact_checker_slugs", slug);
        });
      }

      const response = await authApi.get(
        `/api/admin/posts-date-range/fact-check-eligible-count?${params.toString()}`
      );
      setDateRange((prev) => ({
        ...prev,
        postCount: response.data.post_count,
      }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to count posts");
      setDateRange((prev) => ({ ...prev, postCount: null }));
    } finally {
      setDateRange((prev) => ({ ...prev, isCountingPosts: false }));
    }
  };

  const fetchJobStatus = async () => {
    if (!jobState.currentJob) return;

    try {
      const response = await authApi.get(
        `/api/admin/batch-fact-check/${jobState.currentJob.job_id}/status`
      );

      const newJob = {
        ...response.data,
        errors: response.data.errors || [],
      };

      setJobState({
        currentJob: newJob,
        isRunning: newJob.status === "running",
      });
    } catch (err: any) {
      console.error("Failed to fetch job status:", err);
    }
  };

  const handleFactCheckerToggle = (slug: string) => {
    setSelectedFactCheckers((prev) => {
      if (prev.includes(slug)) {
        return prev.filter((s) => s !== slug);
      } else {
        return [...prev, slug];
      }
    });
  };

  const handleSelectAll = () => {
    if (factCheckersData?.fact_checkers) {
      const activeSlugs = factCheckersData.fact_checkers
        .filter((fc: any) => fc.is_active)
        .map((fc: any) => fc.slug);
      setSelectedFactCheckers(activeSlugs);
    }
  };

  const handleDeselectAll = () => {
    setSelectedFactCheckers([]);
  };

  const handleStartFactChecking = () => {
    if (!dateRange.startDate || !dateRange.endDate) {
      setError("Please select a date range");
      return;
    }

    if (dateRange.postCount === null || dateRange.postCount === 0) {
      setError(
        "No posts found eligible for fact checking in the selected date range"
      );
      return;
    }

    setShowConfirmation(true);
  };

  const handleConfirmFactChecking = async () => {
    if (!dateRange.startDate || !dateRange.endDate) return;

    setShowConfirmation(false);
    setJobState({ currentJob: null, isRunning: true });
    setError(null);

    try {
      // Build params with proper array formatting for FastAPI
      const params = new URLSearchParams();
      params.append("start_date", dateRange.startDate.toISOString());
      params.append("end_date", dateRange.endDate.toISOString());
      params.append("force", "false");

      // Add each fact checker slug as a separate parameter
      if (selectedFactCheckers.length > 0) {
        selectedFactCheckers.forEach((slug) => {
          params.append("fact_checker_slugs", slug);
        });
      }
      // If no fact checkers selected, it will use all active fact checkers

      const response = await authApi.post(
        `/api/admin/batch-fact-check?${params.toString()}`,
        null
      );

      // Get the job ID and start polling immediately
      const jobId = response.data.job_id;

      // Set initial job state and start polling
      setJobState({
        currentJob: {
          job_id: jobId,
          total_posts: response.data.total_posts,
          processed: 0,
          fact_checks_triggered: 0,
          skipped: 0,
          errors: [],
          status: "running",
          progress_percentage: 0,
          started_at: new Date().toISOString(),
        },
        isRunning: true,
      });

      // Poll will get the actual status
      setTimeout(fetchJobStatus, 100);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Failed to start batch fact checking"
      );
      setJobState({ currentJob: null, isRunning: false });
    }
  };

  const activeFactCheckers =
    factCheckersData?.fact_checkers?.filter((fc: any) => fc.is_active) || [];

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-2">Admin: Batch Fact Checking</h1>
      <p className="text-gray-600 mb-8">
        Run fact checkers on posts within a specific date range that don&apos;t
        already have fact checks
      </p>

      {/* Date Range Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Select Date & Time Range</CardTitle>
          <CardDescription>
            Choose the time period for posts to fact-check based on ingested_at
            timestamp
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SimpleDateRangePicker
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
            onStartDateChange={(date) =>
              setDateRange((prev) => ({
                ...prev,
                startDate: date || undefined,
              }))
            }
            onEndDateChange={(date) =>
              setDateRange((prev) => ({ ...prev, endDate: date || undefined }))
            }
            disabled={jobState.isRunning}
          />

          {dateRange.isCountingPosts && (
            <div className="mt-4 flex items-center text-sm text-gray-600">
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Counting eligible posts...
            </div>
          )}

          {dateRange.postCount !== null && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium">
                Found{" "}
                <span className="font-bold text-blue-600">
                  {dateRange.postCount}
                </span>{" "}
                posts
                {dateRange.postCount > 0 && " eligible for fact checking"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Fact Checker Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Select Fact Checkers</CardTitle>
          <CardDescription>
            Choose which fact checkers to run on the posts (leave empty to run
            all active fact checkers)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingFactCheckers ? (
            <div className="flex items-center">
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Loading fact checkers...
            </div>
          ) : (
            <>
              <div className="mb-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSelectAll}
                  disabled={jobState.isRunning}
                >
                  Select All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDeselectAll}
                  disabled={jobState.isRunning}
                >
                  Deselect All
                </Button>
              </div>

              <div className="space-y-2">
                {activeFactCheckers.map((factChecker: any) => (
                  <div
                    key={factChecker.slug}
                    className="flex items-center space-x-2"
                  >
                    <Checkbox
                      id={factChecker.slug}
                      checked={selectedFactCheckers.includes(factChecker.slug)}
                      onCheckedChange={() =>
                        handleFactCheckerToggle(factChecker.slug)
                      }
                      disabled={jobState.isRunning}
                    />
                    <label
                      htmlFor={factChecker.slug}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {factChecker.name}
                      <span className="text-xs text-gray-500 ml-2">
                        ({factChecker.slug})
                      </span>
                    </label>
                  </div>
                ))}
              </div>

              {selectedFactCheckers.length > 0 && (
                <div className="mt-4 text-sm text-gray-600">
                  Selected: {selectedFactCheckers.length} fact checker
                  {selectedFactCheckers.length !== 1 && "s"}
                </div>
              )}

              {selectedFactCheckers.length === 0 && (
                <div className="mt-4 text-sm text-blue-600">
                  ℹ️ No fact checkers selected - will run all active fact
                  checkers
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Job Progress */}
      {jobState.currentJob && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              {jobState.currentJob.status === "running" && (
                <>
                  <Loader2 className="animate-spin mr-2 h-5 w-5" />
                  Processing...
                </>
              )}
              {jobState.currentJob.status === "completed" && (
                <>
                  <CheckCircle className="mr-2 h-5 w-5 text-green-600" />
                  Completed
                </>
              )}
              {jobState.currentJob.status === "failed" && (
                <>
                  <XCircle className="mr-2 h-5 w-5 text-red-600" />
                  Failed
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>
                  {jobState.currentJob.processed} /{" "}
                  {jobState.currentJob.total_posts} posts
                </span>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${jobState.currentJob.progress_percentage}%`,
                  }}
                />
              </div>

              <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                <div>
                  <span className="text-gray-600">Fact Checks Triggered:</span>
                  <span className="ml-2 font-medium">
                    {jobState.currentJob.fact_checks_triggered}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Skipped (Not Eligible):</span>
                  <span className="ml-2 font-medium">
                    {jobState.currentJob.skipped}
                  </span>
                </div>
              </div>

              {jobState.currentJob.errors &&
                jobState.currentJob.errors.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-red-600 mb-1">
                      Errors:
                    </p>
                    <ul className="text-xs text-red-600 list-disc list-inside">
                      {jobState.currentJob.errors
                        .slice(0, 5)
                        .map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      {jobState.currentJob.errors.length > 5 && (
                        <li>
                          ... and {jobState.currentJob.errors.length - 5} more
                        </li>
                      )}
                    </ul>
                  </div>
                )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <Alert className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Confirm Batch Fact Checking</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>You are about to run fact checkers on:</p>
            <ul className="list-disc list-inside ml-4 text-sm">
              <li>
                <strong>{dateRange.postCount}</strong> eligible posts
              </li>
              <li>
                <strong>
                  {selectedFactCheckers.length > 0
                    ? `${selectedFactCheckers.length} fact checker${
                        selectedFactCheckers.length !== 1 ? "s" : ""
                      }`
                    : "All active fact checkers"}
                </strong>
              </li>
            </ul>
            <p className="text-sm text-blue-600 mt-2">
              ℹ️ This will only create fact checks for posts that don&apos;t
              already have them.
            </p>
            <div className="flex gap-2 mt-4">
              <Button
                onClick={handleConfirmFactChecking}
                disabled={jobState.isRunning}
              >
                Yes, Start Fact Checking
              </Button>
              <Button
                onClick={() => setShowConfirmation(false)}
                variant="outline"
                disabled={jobState.isRunning}
              >
                Cancel
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Action Button */}
      {!showConfirmation && !jobState.currentJob && (
        <Button
          onClick={handleStartFactChecking}
          disabled={
            !dateRange.startDate ||
            !dateRange.endDate ||
            jobState.isRunning ||
            dateRange.isCountingPosts
          }
          className="w-full"
        >
          {jobState.isRunning ? (
            <>
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Processing...
            </>
          ) : (
            "Start Batch Fact Checking"
          )}
        </Button>
      )}

      {/* New Job Button */}
      {jobState.currentJob &&
        (jobState.currentJob.status === "completed" ||
          jobState.currentJob.status === "failed") && (
          <Button
            onClick={() => {
              setJobState({ currentJob: null, isRunning: false });
              setShowConfirmation(false);
            }}
            className="w-full"
          >
            Start New Batch Fact Check
          </Button>
        )}
    </div>
  );
}
