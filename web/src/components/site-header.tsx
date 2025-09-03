import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { UserButton, SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <div className="flex items-center">
            <Link href="/">
              <h1 className="text-2xl font-bold text-gray-900">OpenNoteNetwork</h1>
            </Link>
            <Badge variant="secondary" className="ml-3">Public Beta</Badge>
          </div>
          
          <div className="flex items-center gap-6">
            <nav className="hidden md:flex space-x-8">
              <Link href="/posts" className="text-gray-900 hover:text-gray-600">Posts</Link>
              <Link href="/about" className="text-gray-500 hover:text-gray-900">About</Link>
            </nav>
            
            <div className="flex items-center gap-2">
              <SignedOut>
                <SignInButton mode="modal">
                  <Button variant="outline" size="sm">Sign In</Button>
                </SignInButton>
              </SignedOut>
              <SignedIn>
                <UserButton afterSignOutUrl="/" />
              </SignedIn>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}