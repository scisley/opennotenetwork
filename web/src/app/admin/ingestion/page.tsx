"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { useAuthenticatedApi } from '@/lib/auth-axios'
import { AlertCircle, Loader2, CheckCircle, PlayCircle, XCircle } from 'lucide-react'
import { useClassifiers } from '@/hooks/use-api'

interface IngestParams {
  batchSize: number
  maxTotalPosts: number
  duplicateThreshold: number
  autoClassify: boolean
  classifierSlugs: string[]
}

interface JobStatus {
  job_id: string
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  batch_size: number
  max_total_posts: number
  new_posts: number
  updated_posts: number
  posts_processed: number
  duplicate_ratio: number
  current_batch: number
  message: string
  errors: string[]
}

export default function IngestionPage() {
  const [params, setParams] = useState<IngestParams>({
    batchSize: 50,
    maxTotalPosts: 500,
    duplicateThreshold: 0.7,
    autoClassify: true,
    classifierSlugs: []
  })
  
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const authApi = useAuthenticatedApi()
  const { data: classifiersData } = useClassifiers()
  
  const activeClassifiers = classifiersData?.classifiers?.filter(c => c.is_active) || []

  // Poll for job status
  useEffect(() => {
    if (!currentJob || currentJob.status !== 'running') return

    const interval = setInterval(async () => {
      try {
        const response = await authApi.get(
          `/api/admin/ingest/${currentJob.job_id}/status`
        )
        
        setCurrentJob(response.data)
        
        // Stop polling if job is complete
        if (response.data.status !== 'running') {
          clearInterval(interval)
        }
      } catch (err) {
        console.error('Failed to fetch job status:', err)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [currentJob?.job_id, currentJob?.status, authApi])

  const handleStartIngestion = async () => {
    setIsStarting(true)
    setError(null)
    setCurrentJob(null)
    
    try {
      // Build query parameters
      const queryParams = new URLSearchParams({
        batch_size: params.batchSize.toString(),
        max_total_posts: params.maxTotalPosts.toString(),
        duplicate_threshold: params.duplicateThreshold.toString(),
        auto_classify: params.autoClassify.toString()
      })
      
      // Add classifier slugs if any are selected
      if (params.classifierSlugs.length > 0) {
        params.classifierSlugs.forEach(slug => {
          queryParams.append('classifier_slugs', slug)
        })
      }
      
      const response = await authApi.post(
        `/api/admin/ingest?${queryParams.toString()}`
      )
      
      // Immediately fetch the initial status
      const statusResponse = await authApi.get(
        `/api/admin/ingest/${response.data.job_id}/status`
      )
      
      setCurrentJob(statusResponse.data)
    } catch (err: any) {
      console.error('Failed to start ingestion:', err)
      setError(err.response?.data?.detail || 'Failed to start ingestion')
    } finally {
      setIsStarting(false)
    }
  }
  
  const handleClassifierToggle = (slug: string) => {
    setParams(prev => ({
      ...prev,
      classifierSlugs: prev.classifierSlugs.includes(slug)
        ? prev.classifierSlugs.filter(s => s !== slug)
        : [...prev.classifierSlugs, slug]
    }))
  }

  const isRunning = currentJob?.status === 'running'
  const isCompleted = currentJob?.status === 'completed'
  const isFailed = currentJob?.status === 'failed'
  
  // Calculate progress percentage
  const progressPercentage = currentJob && currentJob.max_total_posts > 0
    ? Math.min(100, (currentJob.posts_processed / currentJob.max_total_posts) * 100)
    : 0

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">X.com Post Ingestion</h1>
      
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Ingestion Parameters</CardTitle>
          <CardDescription>
            Configure how posts are fetched from X.com Community Notes API
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="batchSize">Batch Size</Label>
              <Input
                id="batchSize"
                type="number"
                min="1"
                max="100"
                value={params.batchSize}
                onChange={(e) => setParams(prev => ({ 
                  ...prev, 
                  batchSize: parseInt(e.target.value) || 50 
                }))}
                disabled={isRunning}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Posts per API request (max 100)
              </p>
            </div>
            
            <div>
              <Label htmlFor="maxTotalPosts">Max Total Posts</Label>
              <Input
                id="maxTotalPosts"
                type="number"
                min="1"
                max="5000"
                value={params.maxTotalPosts}
                onChange={(e) => setParams(prev => ({ 
                  ...prev, 
                  maxTotalPosts: parseInt(e.target.value) || 500 
                }))}
                disabled={isRunning}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Maximum posts to process in this run
              </p>
            </div>
          </div>
          
          <div>
            <Label htmlFor="duplicateThreshold">Duplicate Threshold</Label>
            <Input
              id="duplicateThreshold"
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={params.duplicateThreshold}
              onChange={(e) => setParams(prev => ({ 
                ...prev, 
                duplicateThreshold: parseFloat(e.target.value) || 0.7 
              }))}
              disabled={isRunning}
            />
            <p className="text-sm text-muted-foreground mt-1">
              Stop ingestion when this ratio of posts are duplicates (0.7 = 70%)
            </p>
          </div>
          
          <div>
            <div className="flex items-center space-x-2 mb-4">
              <Checkbox
                id="autoClassify"
                checked={params.autoClassify}
                onCheckedChange={(checked) => setParams(prev => ({ 
                  ...prev, 
                  autoClassify: checked === true 
                }))}
                disabled={isRunning}
              />
              <Label 
                htmlFor="autoClassify" 
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Auto-classify new posts
              </Label>
            </div>
            
            {params.autoClassify && activeClassifiers.length > 0 && (
              <div className="ml-6 space-y-2">
                <Label className="text-sm">Select Classifiers (optional)</Label>
                <div className="border rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
                  {activeClassifiers.map(classifier => (
                    <div key={classifier.slug} className="flex items-center space-x-2">
                      <Checkbox
                        id={classifier.slug}
                        checked={params.classifierSlugs.includes(classifier.slug)}
                        onCheckedChange={() => handleClassifierToggle(classifier.slug)}
                        disabled={isRunning}
                      />
                      <Label 
                        htmlFor={classifier.slug}
                        className="text-sm cursor-pointer"
                      >
                        {classifier.display_name}
                      </Label>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-muted-foreground">
                  Leave empty to run all active classifiers
                </p>
              </div>
            )}
          </div>
          
          <Button 
            onClick={handleStartIngestion} 
            disabled={isStarting || isRunning}
            className="w-full"
            size="lg"
          >
            {isStarting || isRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isStarting ? 'Starting...' : 'Ingesting Posts...'}
              </>
            ) : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" />
                Start Ingestion
              </>
            )}
          </Button>
        </CardContent>
      </Card>
      
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {currentJob && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {isRunning && (
                <>
                  <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  Ingestion in Progress
                </>
              )}
              {isCompleted && (
                <>
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  Ingestion Complete
                </>
              )}
              {isFailed && (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Ingestion Failed
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isRunning && (
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span>{currentJob.message}</span>
                  <span>{progressPercentage.toFixed(0)}%</span>
                </div>
                <Progress value={progressPercentage} className="w-full" />
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">New Posts</p>
                <p className="text-2xl font-bold text-green-600">{currentJob.new_posts}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Updated Posts</p>
                <p className="text-2xl font-bold text-blue-600">{currentJob.updated_posts}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Processed</p>
                <p className="text-2xl font-bold">{currentJob.posts_processed}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Duplicate Ratio</p>
                <p className="text-2xl font-bold">
                  {(currentJob.duplicate_ratio * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            
            {currentJob.message && (
              <Alert className="mt-4">
                <AlertDescription>{currentJob.message}</AlertDescription>
              </Alert>
            )}
            
            {currentJob.errors && currentJob.errors.length > 0 && (
              <Alert variant="destructive" className="mt-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-semibold mb-1">Errors:</div>
                  {currentJob.errors.map((error, idx) => (
                    <div key={idx} className="text-sm">{error}</div>
                  ))}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}