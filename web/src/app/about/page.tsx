import { SiteHeader } from "@/components/site-header";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">About OpenNoteNetwork</h1>
      
      <div className="prose prose-lg max-w-none space-y-6">
        <section>
          <h2 className="text-2xl font-semibold mb-4">Our Mission</h2>
          <p className="text-gray-700 dark:text-gray-300">
            OpenNoteNetwork is an open-source AI-powered fact-checking network that generates 
            and submits Community Notes to X.com. We aim to combat misinformation by providing 
            accurate, timely, and transparent fact-checking at scale.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
          <div className="space-y-3">
            <div>
              <h3 className="text-xl font-medium">1. Ingestion</h3>
              <p className="text-gray-700 dark:text-gray-300">
                We automatically fetch posts eligible for Community Notes from X.com.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-medium">2. Classification</h3>
              <p className="text-gray-700 dark:text-gray-300">
                AI classifiers categorize posts by topic (climate, politics, health, science, etc.).
              </p>
            </div>
            <div>
              <h3 className="text-xl font-medium">3. Fact-Checking</h3>
              <p className="text-gray-700 dark:text-gray-300">
                Advanced AI agents generate comprehensive fact-checks and concise Community Notes.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-medium">4. Review</h3>
              <p className="text-gray-700 dark:text-gray-300">
                Human reviewers approve and edit generated notes before submission.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-medium">5. Submission</h3>
              <p className="text-gray-700 dark:text-gray-300">
                Approved notes are submitted to X.com's Community Notes system.
              </p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Open Source</h2>
          <p className="text-gray-700 dark:text-gray-300">
            OpenNoteNetwork is fully open source. Our code, classifiers, and fact-checking 
            agents are transparent and available for public review and contribution. We believe 
            transparency is essential for building trust in automated fact-checking systems.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Get Involved</h2>
          <p className="text-gray-700 dark:text-gray-300">
            Interested in contributing? Check out our GitHub repository or contact us to learn 
            how you can help improve fact-checking and combat misinformation online.
          </p>
        </section>
      </div>
      </div>
    </div>
  );
}