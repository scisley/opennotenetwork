import { SiteHeader } from "@/components/site-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { auth } from "@clerk/nextjs/server";

export default async function AdminPage() {
  const { userId } = await auth();

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
          <p className="text-gray-600">
            Manage ingestion, classification, and note generation
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Ingestion</CardTitle>
              <CardDescription>
                Fetch new posts from X.com Community Notes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" disabled>
                Trigger Ingestion
              </Button>
              <p className="text-sm text-gray-500 mt-2">
                API endpoint: POST /api/admin/ingest
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Classification</CardTitle>
              <CardDescription>
                Manage and run classifiers on posts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/admin/classifier-reruns">
                <Button className="w-full">
                  Classifier Reruns
                </Button>
              </Link>
              <p className="text-sm text-gray-500 mt-2">
                Run classifiers on existing posts
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Note Generation</CardTitle>
              <CardDescription>
                Generate and review fact-checks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" disabled>
                Generate Notes
              </Button>
              <p className="text-sm text-gray-500 mt-2">
                Coming soon
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Submissions</CardTitle>
              <CardDescription>
                Review and submit notes to X.com
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" disabled>
                Review Queue
              </Button>
              <p className="text-sm text-gray-500 mt-2">
                0 notes pending review
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Reconciliation</CardTitle>
              <CardDescription>
                Check status of submitted notes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" disabled>
                Check Status
              </Button>
              <p className="text-sm text-gray-500 mt-2">
                API endpoint: POST /api/admin/reconcile
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>
                Manage user roles and access
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" disabled>
                Manage Users
              </Button>
              <p className="text-sm text-gray-500 mt-2">
                Current user ID: {userId || 'Not authenticated'}
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}