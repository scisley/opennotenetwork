'use client';

import Link from "next/link";
import { UserButton, SignInButton, SignedIn, SignedOut, useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { FileText, Info, Settings, Menu } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export function SiteHeader() {
  const { sessionClaims } = useAuth();
  const userRole = (sessionClaims as any)?.metadata?.role;
  const isAdmin = userRole === "admin";

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <div className="flex items-center">
            <Link href="/">
              <h1 className="text-2xl font-bold text-gray-900">OpenNoteNetwork</h1>
            </Link>
          </div>

          <div className="flex items-center gap-6">
            <nav className="hidden md:flex space-x-8">
              <Link href="/posts" className="text-gray-900 hover:text-gray-600">Posts</Link>
              <Link href="/about" className="text-gray-500 hover:text-gray-900">About</Link>
              {isAdmin && (
                <Link href="/admin" className="text-gray-900 hover:text-gray-600">Admin</Link>
              )}
            </nav>

            <div className="flex items-center gap-2">
              <SignedOut>
                {/* Desktop: Show Sign In button */}
                <div className="hidden md:block">
                  <SignInButton mode="modal">
                    <Button variant="outline" size="sm">Sign In</Button>
                  </SignInButton>
                </div>

                {/* Mobile: Show hamburger menu for guests */}
                <div className="md:hidden">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <Menu className="h-5 w-5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuItem asChild>
                        <Link href="/posts" className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          Posts
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/about" className="flex items-center gap-2">
                          <Info className="h-4 w-4" />
                          About
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem asChild>
                        <SignInButton mode="modal">
                          <button className="w-full text-left">Sign In</button>
                        </SignInButton>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </SignedOut>

              <SignedIn>
                <UserButton afterSignOutUrl="/">
                  <UserButton.MenuItems>
                    <UserButton.Link
                      label="Posts"
                      labelIcon={<FileText className="h-4 w-4" />}
                      href="/posts"
                    />
                    <UserButton.Link
                      label="About"
                      labelIcon={<Info className="h-4 w-4" />}
                      href="/about"
                    />
                    {isAdmin && (
                      <UserButton.Link
                        label="Admin"
                        labelIcon={<Settings className="h-4 w-4" />}
                        href="/admin"
                      />
                    )}
                  </UserButton.MenuItems>
                </UserButton>
              </SignedIn>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}