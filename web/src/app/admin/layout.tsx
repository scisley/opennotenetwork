"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PlayCircle, RefreshCw, Shield, ChevronRight, Send, CheckCircle, ListTodo, Menu, X } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navItems = [
    {
      href: "/admin/ingestion",
      label: "Ingestion",
      icon: PlayCircle,
      description: "Fetch posts from X.com",
    },
    {
      href: "/admin/classifier-reruns",
      label: "Classifier Reruns",
      icon: RefreshCw,
      description: "Batch reclassify posts",
    },
    {
      href: "/admin/fact-check-batch",
      label: "Batch Fact Check",
      icon: CheckCircle,
      description: "Run fact checkers on posts",
    },
    {
      href: "/admin/submission-queue",
      label: "Submission Queue",
      icon: ListTodo,
      description: "Notes ready for submission",
    },
    {
      href: "/admin/submissions",
      label: "Submissions Review",
      icon: Send,
      description: "Community Notes status",
    },
  ];

  return (
    <div className="flex min-h-screen">
      {/* Mobile header with menu button */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <h2 className="text-lg font-bold">Admin Panel</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-64 bg-gray-50 border-r
        transform transition-transform duration-300 ease-in-out
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-6 mt-16 lg:mt-0">
          <div className="hidden lg:flex items-center gap-2 mb-8">
            <Shield className="h-6 w-6" />
            <h2 className="text-xl font-bold">Admin Panel</h2>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)}>
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-gray-100"
                  >
                    <Icon className="mr-3 h-4 w-4" />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 opacity-50" />
                  </Button>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 pt-8 border-t">
            <Link href="/" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" className="w-full">
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-white pt-16 lg:pt-0">{children}</main>
    </div>
  );
}
