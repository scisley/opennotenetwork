import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PlayCircle, RefreshCw, Shield, ChevronRight } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
  ];

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-50 border-r">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-8">
            <Shield className="h-6 w-6" />
            <h2 className="text-xl font-bold">Admin Panel</h2>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href}>
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
            <Link href="/">
              <Button variant="outline" className="w-full">
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-white">{children}</main>
    </div>
  );
}
