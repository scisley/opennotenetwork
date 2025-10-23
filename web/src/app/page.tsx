import Link from "next/link";
import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/site-header";
import { ArrowRight, Shield, Brain, CheckCircle, Scale, Globe } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-white">
      <SiteHeader />

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="absolute inset-0 bg-grid-slate-100 [mask-image:radial-gradient(ellipse_at_center,transparent,white)] opacity-10"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
              Fighting Misinformation with
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600"> AI-Powered </span>
              Fact-Checking
            </h1>
            <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              OpenNoteNetwork leverages advanced AI to identify and fact-check misleading content on social media,
              contributing verified Community Notes to combat misinformation.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/posts">
                <Button size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-6 text-lg rounded-full shadow-lg hover:shadow-xl transition-all">
                  Explore Posts
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* What We Do Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              What is OpenNoteNetwork?
            </h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              We&apos;re building an intelligent system that automatically identifies potentially misleading posts on X (formerly Twitter)
              and generates fact-checked Community Notes to help users make informed decisions.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Brain className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">AI-Powered Analysis</h3>
              <p className="text-gray-600">
                Advanced language models analyze posts across multiple domains including climate, science, health, and politics.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Scale className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Balanced Perspective</h3>
              <p className="text-gray-600">
                Addresses misinformation from across the political spectrum, fact-checking claims from both left and right viewpoints.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Key Features Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-16">
            Why OpenNoteNetwork?
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <Shield className="h-10 w-10 text-blue-600 mb-4" />
              <h3 className="font-semibold text-lg mb-2">Verified Sources</h3>
              <p className="text-gray-600 text-sm">
                Every fact-check includes citations from reputable sources and scientific literature.
              </p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <Globe className="h-10 w-10 text-purple-600 mb-4" />
              <h3 className="font-semibold text-lg mb-2">Multi-Domain Coverage</h3>
              <p className="text-gray-600 text-sm">
                Comprehensive fact-checking across climate, science, health, politics, and more.
              </p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <CheckCircle className="h-10 w-10 text-green-600 mb-4" />
              <h3 className="font-semibold text-lg mb-2">Community Notes</h3>
              <p className="text-gray-600 text-sm">
                Direct integration with X&apos;s Community Notes program for maximum impact.
              </p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <Brain className="h-10 w-10 text-orange-600 mb-4" />
              <h3 className="font-semibold text-lg mb-2">Continuous Learning</h3>
              <p className="text-gray-600 text-sm">
                Our AI models improve over time based on community feedback and outcomes.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            Ready to See Our Fact-Checks in Action?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Browse through posts that have been analyzed and fact-checked by our AI system.
          </p>
          <Link href="/posts">
            <Button
              size="lg"
              variant="secondary"
              className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-6 text-lg rounded-full shadow-lg hover:shadow-xl transition-all"
            >
              Explore Posts
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center text-gray-500">
            <p className="text-sm">
              OpenNoteNetwork • AI-Powered Community Notes for X
            </p>
            <p className="text-xs mt-2">
              Fighting misinformation with transparent, fact-based analysis
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}