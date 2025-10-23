import { SiteHeader } from "@/components/site-header";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />

      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">About</h1>

        <div className="prose prose-lg max-w-none">
          <section className="space-y-4 mb-8">
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              This project explores how AI can help write{" "}
              <strong>Community Notes</strong>—short, cited fact-checks that
              provide context on social media posts. The challenge is
              straightforward: misinformation spreads at the speed of social
              media, so fact-checking must keep pace. By combining AI&apos;s
              scalability with the transparency of Community Notes, we&apos;re
              testing whether it&apos;s possible to deliver better information
              exactly where misleading claims are circulating.
            </p>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              Our system monitors posts where Community Notes have been
              requested, automatically drafts potential notes, and makes them
              available for review. The system draws from reliable sources,
              maintains a neutral tone, and covers topics ranging from politics
              and technology to health, science, and breaking news. Our goal is
              to refine this process so that generated notes are not only fast,
              but consistently helpful and trustworthy.
            </p>
          </section>

          <section className="space-y-4 mb-8">
            <h2 className="text-2xl font-semibold mb-4">
              X Community Notes Program
            </h2>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              This work operates within{" "}
              <a
                href="https://communitynotes.x.com/guide/en/api/overview"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                X&apos;s Community Notes API program
              </a>
              , which X.com recently opened to enable AI-generated Community
              Notes. We work within X&apos;s established framework, follow their
              guidelines, and submit notes through their API alongside other
              program participants.
            </p>
          </section>

          <section className="space-y-4 mb-8">
            <h2 className="text-2xl font-semibold mb-4">Early Beta Status</h2>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              This is an <strong>early beta</strong> project, and we expect to
              make mistakes—potentially many of them. Fact-checking is
              inherently challenging: sources conflict, language carries nuance,
              and context matters deeply. Automating this process with AI
              compounds these difficulties. Some of our notes will be
              incomplete, confusing, or incorrect.
            </p>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              Despite these challenges, the potential impact makes the effort
              worthwhile. If we can develop this approach successfully, even
              incrementally, it could provide a scalable method for improving
              information quality online. We&apos;re committed to learning from
              our errors and continuously improving the system.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold mb-4">Help Us Improve</h2>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              Your feedback is essential to this effort. If you notice something
              that appears incorrect, or if you have suggestions for improving
              the system, please share your feedback:
            </p>
            <p className="text-gray-700 dark:text-gray-300">
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSfhF-crfFLPv6P79fAzAAk2QDisv0wKqYdh3JNlqKcGaXjHgA/viewform?usp=header"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline font-medium"
              >
                Submit Feedback
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
