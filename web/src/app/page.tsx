import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiStatus } from "@/components/api-status";
import { SiteHeader } from "@/components/site-header";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">OpenNoteNetwork Community Notes</h2>
          <p className="text-gray-600 max-w-2xl">
            AI-powered fact-checking network for posts on social media. 
            View submitted and accepted Community Notes with detailed fact-checks and reliable sources.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Recent Notes
                <Badge variant="outline">Coming Soon</Badge>
              </CardTitle>
              <CardDescription>
                Latest fact-checks submitted to X.com Community Notes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                No notes available yet. The ingestion system has collected posts and is ready for classification and note generation.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Topics
                <Badge variant="outline">Multi-Domain</Badge>
              </CardTitle>
              <CardDescription>
                Browse notes by topic area
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge>Climate Change</Badge>
                <Badge variant="secondary">Science</Badge>
                <Badge variant="secondary">Energy</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>System Status</CardTitle>
              <CardDescription>
                Backend integration status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ApiStatus />
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 text-center">
          <Link href="/posts">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
              Browse All Posts →
            </Button>
          </Link>
        </div>

        <div className="mt-12 text-center">
          <h3 className="text-xl font-semibold mb-4">How It Works</h3>
          <div className="grid gap-4 md:grid-cols-4 text-sm">
            <div className="space-y-2">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold mx-auto">1</div>
              <h4 className="font-medium">Ingestion</h4>
              <p className="text-gray-600">Posts are collected from X.com Community Notes API</p>
            </div>
            <div className="space-y-2">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-semibold mx-auto">2</div>
              <h4 className="font-medium">Classification</h4>
              <p className="text-gray-600">AI identifies content across multiple domains for fact-checking</p>
            </div>
            <div className="space-y-2">
              <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-semibold mx-auto">3</div>
              <h4 className="font-medium">Generation</h4>
              <p className="text-gray-600">LangGraph agent creates detailed fact-checks and concise notes</p>
            </div>
            <div className="space-y-2">
              <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-semibold mx-auto">4</div>
              <h4 className="font-medium">Review & Submit</h4>
              <p className="text-gray-600">Human reviewers approve notes before submission to X.com</p>
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>OpenNoteNetwork • Open Source Framework for Community Notes</p>
            <p className="mt-2">Backend API running on localhost:8000</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
