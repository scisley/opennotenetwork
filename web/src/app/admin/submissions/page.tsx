"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSubmissionsSummary, useUpdateSubmissionStatuses, useSubmissions, useWritingLimit } from '@/hooks/use-api'
import {
  AlertCircle, CheckCircle, XCircle, Clock, RefreshCw, FileText,
  Search, ChevronLeft, ChevronRight
} from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function SubmissionsPage() {
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const limit = 25

  const { data: summary, isLoading: summaryLoading, refetch: refetchSummary } = useSubmissionsSummary()
  const { data: writingLimit, isLoading: writingLimitLoading, refetch: refetchWritingLimit } = useWritingLimit()
  const updateStatuses = useUpdateSubmissionStatuses()

  const { data: submissionsData, isLoading: submissionsLoading, refetch: refetchSubmissions } = useSubmissions({
    limit,
    offset: page * limit,
    search: search || undefined,
    status: statusFilter || undefined
  })

  const handleUpdateStatuses = async () => {
    setError(null)
    setSuccess(null)

    try {
      const result = await updateStatuses.mutateAsync()
      setSuccess(`Updated ${result.updated_count} submissions from ${result.total_x_notes} X notes`)
      await Promise.all([refetchSummary(), refetchSubmissions(), refetchWritingLimit()])
    } catch (err: any) {
      console.error('Failed to update statuses:', err)
      setError(err.response?.data?.detail || 'Failed to update submission statuses')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'displayed':
      case 'currently_rated_helpful':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'not_displayed':
      case 'currently_rated_not_helpful':
      case 'firm_reject':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'submitted':
      case 'needs_more_ratings':
      case 'insufficient_consensus':
      case 'minimum_ratings_not_met':
        return <Clock className="h-4 w-4 text-yellow-600" />
      case 'submission_failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      case 'pending':
        return <Clock className="h-4 w-4 text-blue-600" />
      default:
        return <FileText className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'displayed':
      case 'currently_rated_helpful':
        return 'bg-green-100 border-green-400 text-green-900 hover:border-green-500'
      case 'not_displayed':
      case 'currently_rated_not_helpful':
      case 'firm_reject':
        return 'bg-red-50 border-red-300 text-red-800 hover:border-red-400'
      case 'submitted':
      case 'needs_more_ratings':
        return 'bg-blue-50 border-blue-300 text-blue-800 hover:border-blue-400'
      case 'insufficient_consensus':
      case 'minimum_ratings_not_met':
        return 'bg-yellow-50 border-yellow-300 text-yellow-800 hover:border-yellow-400'
      case 'submission_failed':
        return 'bg-red-50 border-red-300 text-red-800 hover:border-red-400'
      case 'pending':
        return 'bg-blue-50 border-blue-300 text-blue-800 hover:border-blue-400'
      case 'deleted':
        return 'bg-slate-50 border-slate-300 text-slate-800 hover:border-slate-400'
      default:
        return 'bg-gray-50 border-gray-300 text-gray-800 hover:border-gray-400'
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      currently_rated_helpful: "default",
      currently_rated_not_helpful: "destructive",
      firm_reject: "destructive",
      submitted: "secondary",
      needs_more_ratings: "outline",
      insufficient_consensus: "outline",
      minimum_ratings_not_met: "outline",
      submission_failed: "destructive",
      pending: "outline"
    }

    const formatStatusText = (status: string) => {
      // Format status for display
      switch (status) {
        case 'currently_rated_helpful':
          return 'Helpful'
        case 'currently_rated_not_helpful':
          return 'Not Helpful'
        case 'firm_reject':
          return 'Rejected'
        case 'needs_more_ratings':
          return 'Needs Ratings'
        case 'insufficient_consensus':
          return 'No Consensus'
        case 'minimum_ratings_not_met':
          return 'Min Ratings Not Met'
        case 'submission_failed':
          return 'Failed'
        default:
          return status.replace(/_/g, ' ')
      }
    }

    return (
      <Badge variant={variants[status] || "outline"} className="flex items-center gap-1 w-fit">
        {getStatusIcon(status)}
        {formatStatusText(status)}
      </Badge>
    )
  }

  const totalPages = Math.ceil((submissionsData?.total || 0) / limit)

  if (summaryLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500">Loading submission statistics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-4 md:space-y-6">
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-4 md:mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Community Notes Submissions</h1>
          <p className="text-sm md:text-base text-gray-600 mt-1">Monitor and track submitted notes status on X.com</p>
        </div>
        <Button
          onClick={handleUpdateStatuses}
          disabled={updateStatuses.isPending}
          size="lg"
          className="w-full md:w-auto"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${updateStatuses.isPending ? 'animate-spin' : ''}`} />
          Update All Statuses
        </Button>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {summary && Object.entries(summary.status_counts)
          .filter(([status]) => status !== 'pending')
          .sort(([a], [b]) => {
            // Move submission_failed to end
            if (a === 'submission_failed') return 1
            if (b === 'submission_failed') return -1
            return 0
          })
          .map(([status, count]) => (
          <Card key={status} className={`border ${getStatusColor(status)}`}>
            <CardContent className="p-2">
              <div className="flex flex-col items-center text-center space-y-1">
                <div className="p-1 rounded-full bg-white/50">
                  {getStatusIcon(status)}
                </div>
                <span className="text-lg sm:text-xl font-bold tabular-nums">{count as number}</span>
                <p className="text-[10px] sm:text-xs font-medium capitalize leading-tight">
                  {status === 'displayed' ? 'Community Rated Helpful' :
                   status === 'currently_rated_helpful' ? 'Community Rated Helpful' :
                   status === 'not_displayed' ? 'Community Rated Not Helpful' :
                   status === 'currently_rated_not_helpful' ? 'Community Rated Not Helpful' :
                   status === 'needs_more_ratings' ? 'Needs Ratings' :
                   status === 'insufficient_consensus' ? 'No Consensus' :
                   status === 'minimum_ratings_not_met' ? 'Min Ratings' :
                   status === 'firm_reject' ? 'Rejected' :
                   status.replace(/_/g, ' ')}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Summary Statistics and Writing Limit - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Total and Last Update */}
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Summary Statistics</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-2">
            <div className="flex items-center justify-between p-2 bg-white rounded">
              <span className="text-sm text-gray-700 font-medium">Total Submissions</span>
              <Badge variant="secondary" className="text-base px-3 py-0">
                {summary?.total || 0}
              </Badge>
            </div>

            {summary?.last_status_update && (
              <div className="flex items-center justify-between p-2 bg-white rounded">
                <span className="text-sm text-gray-700 font-medium">Last Status Update</span>
                <span className="text-xs font-mono">
                  {new Date(summary.last_status_update).toLocaleString()}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* X.com Daily Writing Limit */}
        <Card className={`border ${
          writingLimitLoading ? 'bg-gray-50' :
          !writingLimit || writingLimit.total_notes < 5 ? 'bg-gray-50 border-gray-300' :
          writingLimit.writing_limit >= 10 ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-300' :
          writingLimit.writing_limit >= 5 ? 'bg-gradient-to-r from-yellow-50 to-amber-50 border-yellow-300' :
          'bg-gradient-to-r from-red-50 to-rose-50 border-red-300'
        }`}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">X.com Daily Writing Limit</CardTitle>
              {writingLimit && writingLimit.notes_without_status > 0 && (
                <Badge variant="outline" className="text-xs py-0">
                  {writingLimit.notes_without_status} pending
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="pt-0 space-y-1.5">
            {writingLimitLoading ? (
              <div className="text-center py-2">
                <p className="text-xs text-gray-500">Calculating...</p>
              </div>
            ) : !writingLimit || writingLimit.total_notes < 5 ? (
              <div className="text-center py-2">
                <p className="text-xs text-gray-600">Insufficient data (need 5+ notes)</p>
              </div>
            ) : (
              <>
                {/* Daily Limit - Inline with metrics */}
                <div className="grid grid-cols-4 gap-1.5">
                  <div className="col-span-4 p-1.5 bg-white rounded border text-center">
                    <div className="text-xs text-gray-500">Daily Limit</div>
                    <div className={`text-2xl font-bold tabular-nums ${
                      writingLimit.writing_limit >= 10 ? 'text-green-600' :
                      writingLimit.writing_limit >= 5 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {writingLimit.writing_limit}
                    </div>
                  </div>
                  <div className="p-1.5 bg-white rounded border text-center">
                    <div className="text-xs text-gray-500">NH₅</div>
                    <div className="text-sm font-bold">{writingLimit.nh_5}</div>
                  </div>
                  <div className="p-1.5 bg-white rounded border text-center">
                    <div className="text-xs text-gray-500">NH₁₀</div>
                    <div className="text-sm font-bold">{writingLimit.nh_10}</div>
                  </div>
                  <div className="p-1.5 bg-white rounded border text-center">
                    <div className="text-xs text-gray-500">HR₂₀</div>
                    <div className="text-sm font-bold">{(writingLimit.hr_r * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-1.5 bg-white rounded border text-center">
                    <div className="text-xs text-gray-500">HR₁₀₀</div>
                    <div className="text-sm font-bold">{(writingLimit.hr_l * 100).toFixed(0)}%</div>
                  </div>
                </div>

                <div className="text-xs text-gray-400 text-center">
                  DN₃₀: {writingLimit.dn_30.toFixed(1)} | Total: {writingLimit.total_notes} | {new Date(writingLimit.calculated_at).toLocaleTimeString()}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Searchable Table Section */}
      <Card>
        <CardHeader>
          <CardTitle>All Submissions</CardTitle>
          <CardDescription>Search and browse submitted Community Notes</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 md:px-6 px-2">
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search notes, posts, or X note IDs..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(0)
                }}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter || "all"} onValueChange={(val) => {
              setStatusFilter(val === "all" ? "" : val)
              setPage(0)
            }}>
              <SelectTrigger className="w-full sm:w-[220px]">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="currently_rated_helpful">Helpful</SelectItem>
                <SelectItem value="currently_rated_not_helpful">Not Helpful</SelectItem>
                <SelectItem value="firm_reject">Rejected</SelectItem>
                <SelectItem value="submitted">Submitted</SelectItem>
                <SelectItem value="needs_more_ratings">Needs Ratings</SelectItem>
                <SelectItem value="insufficient_consensus">No Consensus</SelectItem>
                <SelectItem value="minimum_ratings_not_met">Min Ratings Not Met</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="submission_failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Results Table */}
          {submissionsLoading ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Loading submissions...</p>
            </div>
          ) : (
            <>
              {/* Desktop Table View */}
              <div className="hidden md:block border rounded-lg overflow-x-auto">
                <Table className="min-w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px] min-w-[100px]">Date</TableHead>
                      <TableHead className="w-[150px] min-w-[150px]">Status</TableHead>
                      <TableHead className="min-w-[300px] max-w-[500px]">Note Text</TableHead>
                      <TableHead className="w-[80px] min-w-[80px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {submissionsData?.submissions?.map((submission: any) => (
                      <TableRow
                        key={submission.submission_id}
                      >
                        <TableCell className="text-sm">
                          {submission.submitted_at ?
                            new Date(submission.submitted_at).toLocaleDateString() :
                            'Not submitted'
                          }
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {getStatusBadge(submission.status)}
                            {submission.x_status && (
                              <span className="text-xs text-gray-500">
                                X: {submission.x_status}
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[500px]">
                          <div className="space-y-1">
                            <p className="text-sm line-clamp-2 break-words">{submission.note_text}</p>
                            <p className="text-xs text-gray-500 line-clamp-1 break-words">
                              Post: {submission.post_text}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                          >
                            <a href={`/posts/${submission.post_uid}/manage`}>
                              Manage
                            </a>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile Card View */}
              <div className="md:hidden space-y-1.5">
                {submissionsData?.submissions?.map((submission: any) => (
                  <Card key={submission.submission_id} className="border py-2 gap-0">
                    <CardContent className="px-2.5 py-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        {getStatusBadge(submission.status)}
                        <div className="text-xs text-gray-500 whitespace-nowrap">
                          {submission.submitted_at ?
                            new Date(submission.submitted_at).toLocaleDateString() :
                            'Not submitted'
                          }
                        </div>
                      </div>

                      <p className="text-sm line-clamp-2 break-words mb-1 leading-tight">{submission.note_text}</p>

                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs text-gray-500 line-clamp-1 break-words flex-1">
                          {submission.post_text}
                        </p>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="shrink-0 h-6 px-2 text-xs"
                          asChild
                        >
                          <a href={`/posts/${submission.post_uid}/manage`}>
                            Manage
                          </a>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {submissionsData?.submissions?.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-gray-500">No submissions found</p>
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                  <p className="text-xs sm:text-sm text-gray-600">
                    Showing {page * limit + 1} to {Math.min((page + 1) * limit, submissionsData?.total || 0)} of {submissionsData?.total || 0}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(0, p - 1))}
                      disabled={page === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      <span className="hidden sm:inline">Previous</span>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => p + 1)}
                      disabled={page >= totalPages - 1}
                    >
                      <span className="hidden sm:inline">Next</span>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
