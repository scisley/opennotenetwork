import { SiteHeader } from "@/components/site-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Card className="text-center">
          <CardHeader>
            <CardTitle className="text-3xl">Welcome to the Admin Panel</CardTitle>
            <CardDescription className="text-lg mt-2">
              Use the navigation options in the left sidebar to manage the system
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    </div>
  );
}