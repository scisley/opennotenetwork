"use client"

import { useState, useEffect } from 'react'
import { SimpleDateRangePicker } from '@/components/ui/simple-date-range-picker'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { useClassifiers } from '@/hooks/use-api'
import axios from 'axios'
import { API_BASE_URL } from '@/lib/api'
import { AlertCircle, Loader2, CheckCircle, XCircle } from 'lucide-react'

interface JobStatus {
  job_id: string
  total_posts: number
  processed: number
  classified: number
  skipped: number
  errors: string[]
  status: 'running' | 'completed' | 'failed'
  progress_percentage: number
  started_at: string
  completed_at?: string
}

interface DateRangeState {
  startDate: Date | undefined
  endDate: Date | undefined
  postCount: number | null
  isCountingPosts: boolean
}

interface JobState {
  currentJob: JobStatus | null
  isRunning: boolean
}

export default function ClassifierRerunsPage() {
  const [dateRange, setDateRange] = useState<DateRangeState>({
    startDate: undefined,
    endDate: undefined,
    postCount: null,
    isCountingPosts: false
  })
  const [jobState, setJobState] = useState<JobState>({
    currentJob: null,
    isRunning: false
  })
  const [selectedClassifiers, setSelectedClassifiers] = useState<string[]>([])
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { data: classifiersData, isLoading: isLoadingClassifiers } = useClassifiers()

  // Fetch post count when dates change
  useEffect(() => {
    if (dateRange.startDate && dateRange.endDate) {
      fetchPostCount()
    } else {
      setDateRange(prev => ({ ...prev, postCount: null }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange.startDate, dateRange.endDate])

  // Poll job status when running
  useEffect(() => {
    if (jobState.currentJob && jobState.currentJob.status === 'running') {
      const interval = setInterval(fetchJobStatus, 4000) // Poll every 4 seconds
      return () => clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobState.currentJob])

  const fetchPostCount = async () => {
    if (!dateRange.startDate || !dateRange.endDate) return
    
    setDateRange(prev => ({ ...prev, isCountingPosts: true }))
    setError(null)
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/admin/posts-date-range/count`, {
        params: {
          start_date: dateRange.startDate.toISOString(),
          end_date: dateRange.endDate.toISOString()
        }
      })
      setDateRange(prev => ({ ...prev, postCount: response.data.post_count }))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to count posts')
      setDateRange(prev => ({ ...prev, postCount: null }))
    } finally {
      setDateRange(prev => ({ ...prev, isCountingPosts: false }))
    }
  }

  const fetchJobStatus = async () => {
    if (!jobState.currentJob) return
    
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/admin/batch-reclassify/${jobState.currentJob.job_id}/status`
      )
      
      const newJob = {
        ...response.data,
        errors: response.data.errors || []
      }
      
      setJobState({
        currentJob: newJob,
        isRunning: newJob.status === 'running'
      })
    } catch (err: any) {
      console.error('Failed to fetch job status:', err)
    }
  }

  const handleClassifierToggle = (slug: string) => {
    setSelectedClassifiers(prev => {
      if (prev.includes(slug)) {
        return prev.filter(s => s !== slug)
      } else {
        return [...prev, slug]
      }
    })
  }

  const handleSelectAll = () => {
    if (classifiersData?.classifiers) {
      const activeSlugs = classifiersData.classifiers
        .filter(c => c.is_active)
        .map(c => c.slug)
      setSelectedClassifiers(activeSlugs)
    }
  }

  const handleDeselectAll = () => {
    setSelectedClassifiers([])
  }

  const handleStartReclassification = () => {
    if (!dateRange.startDate || !dateRange.endDate || selectedClassifiers.length === 0) {
      setError('Please select a date range and at least one classifier')
      return
    }
    
    if (dateRange.postCount === null || dateRange.postCount === 0) {
      setError('No posts found in the selected date range')
      return
    }
    
    setShowConfirmation(true)
  }

  const handleConfirmReclassification = async () => {
    if (!dateRange.startDate || !dateRange.endDate) return
    
    setShowConfirmation(false)
    setJobState({ currentJob: null, isRunning: true })
    setError(null)
    
    try {
      // Build params with proper array formatting for FastAPI
      const params = new URLSearchParams()
      params.append('start_date', dateRange.startDate.toISOString())
      params.append('end_date', dateRange.endDate.toISOString())
      params.append('force', 'true')
      
      // Add each classifier slug as a separate parameter
      if (selectedClassifiers.length > 0) {
        selectedClassifiers.forEach(slug => {
          params.append('classifier_slugs', slug)
        })
      } else {
        // This shouldn't happen due to validation, but just in case
        setError('No classifiers selected')
        return
      }
      
      const response = await axios.post(
        `${API_BASE_URL}/api/admin/batch-reclassify?${params.toString()}`,
        null
      )
      
      // Get the job ID and start polling immediately
      const jobId = response.data.job_id
      
      // Set initial job state and start polling
      setJobState({
        currentJob: { 
          job_id: jobId, 
          total_posts: response.data.total_posts,
          processed: 0,
          classified: 0,
          skipped: 0,
          errors: [],
          status: 'running',
          progress_percentage: 0,
          started_at: new Date().toISOString()
        },
        isRunning: true
      })
      
      // Poll will get the actual status
      setTimeout(fetchJobStatus, 100)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start batch reclassification')
      setJobState({ currentJob: null, isRunning: false })
    }
  }

  const activeClassifiers = classifiersData?.classifiers?.filter(c => c.is_active) || []

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-2">Admin: Classifier Reruns</h1>
      <p className="text-gray-600 mb-8">
        Rerun classifiers on posts within a specific date and time range
      </p>

      {/* Date Range Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Select Date & Time Range</CardTitle>
          <CardDescription>
            Choose the time period for posts to reclassify based on ingested_at timestamp
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SimpleDateRangePicker
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
            onStartDateChange={(date) => setDateRange(prev => ({ ...prev, startDate: date || undefined }))}
            onEndDateChange={(date) => setDateRange(prev => ({ ...prev, endDate: date || undefined }))}
            disabled={jobState.isRunning}
          />
          
          {dateRange.isCountingPosts && (
            <div className="mt-4 flex items-center text-sm text-gray-600">
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Counting posts...
            </div>
          )}
          
          {dateRange.postCount !== null && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium">
                Found <span className="font-bold text-blue-600">{dateRange.postCount}</span> posts
                {dateRange.postCount > 0 && ' that match your criteria'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Classifier Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Select Classifiers</CardTitle>
          <CardDescription>
            Choose which classifiers to run on the posts
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingClassifiers ? (
            <div className="flex items-center">
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Loading classifiers...
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
                {activeClassifiers.map(classifier => (
                  <div key={classifier.slug} className="flex items-center space-x-2">
                    <Checkbox
                      id={classifier.slug}
                      checked={selectedClassifiers.includes(classifier.slug)}
                      onCheckedChange={() => handleClassifierToggle(classifier.slug)}
                      disabled={jobState.isRunning}
                    />
                    <label
                      htmlFor={classifier.slug}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {classifier.display_name}
                      <span className="text-xs text-gray-500 ml-2">({classifier.slug})</span>
                    </label>
                  </div>
                ))}
              </div>
              
              {selectedClassifiers.length > 0 && (
                <div className="mt-4 text-sm text-gray-600">
                  Selected: {selectedClassifiers.length} classifier{selectedClassifiers.length !== 1 && 's'}
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
              {jobState.currentJob.status === 'running' && (
                <>
                  <Loader2 className="animate-spin mr-2 h-5 w-5" />
                  Processing...
                </>
              )}
              {jobState.currentJob.status === 'completed' && (
                <>
                  <CheckCircle className="mr-2 h-5 w-5 text-green-600" />
                  Completed
                </>
              )}
              {jobState.currentJob.status === 'failed' && (
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
                <span>{jobState.currentJob.processed} / {jobState.currentJob.total_posts} posts</span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${jobState.currentJob.progress_percentage}%` }}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                <div>
                  <span className="text-gray-600">Classified:</span>
                  <span className="ml-2 font-medium">{jobState.currentJob.classified}</span>
                </div>
                <div>
                  <span className="text-gray-600">Skipped:</span>
                  <span className="ml-2 font-medium">{jobState.currentJob.skipped}</span>
                </div>
              </div>
              
              {jobState.currentJob.errors && jobState.currentJob.errors.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-red-600 mb-1">Errors:</p>
                  <ul className="text-xs text-red-600 list-disc list-inside">
                    {jobState.currentJob.errors.slice(0, 5).map((error, i) => (
                      <li key={i}>{error}</li>
                    ))}
                    {jobState.currentJob.errors.length > 5 && (
                      <li>... and {jobState.currentJob.errors.length - 5} more</li>
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
          <AlertTitle>Confirm Batch Reclassification</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>You are about to rerun classifiers on:</p>
            <ul className="list-disc list-inside ml-4 text-sm">
              <li><strong>{dateRange.postCount}</strong> posts</li>
              <li><strong>{selectedClassifiers.length}</strong> classifier{selectedClassifiers.length !== 1 && 's'}</li>
            </ul>
            <p className="text-sm text-orange-600 mt-2">
              This will overwrite any existing classifications for the selected classifiers on these posts.
            </p>
            <div className="flex gap-2 mt-4">
              <Button
                onClick={handleConfirmReclassification}
                variant="destructive"
                disabled={jobState.isRunning}
              >
                Yes, Start Reclassification
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
          onClick={handleStartReclassification}
          disabled={!dateRange.startDate || !dateRange.endDate || selectedClassifiers.length === 0 || jobState.isRunning || dateRange.isCountingPosts}
          className="w-full"
        >
          {jobState.isRunning ? (
            <>
              <Loader2 className="animate-spin mr-2 h-4 w-4" />
              Processing...
            </>
          ) : (
            'Start Reclassification'
          )}
        </Button>
      )}

      {/* New Job Button */}
      {jobState.currentJob && (jobState.currentJob.status === 'completed' || jobState.currentJob.status === 'failed') && (
        <Button
          onClick={() => {
            setJobState({ currentJob: null, isRunning: false })
            setShowConfirmation(false)
          }}
          className="w-full"
        >
          Start New Reclassification
        </Button>
      )}
    </div>
  )
}