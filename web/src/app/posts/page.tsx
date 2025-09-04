"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { usePublicPosts } from "@/hooks/use-api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
  X,
  Filter,
} from "lucide-react";
import { ClassificationFilterPanel } from "@/components/filters/classification-filter-panel";
import { ClassificationChipRow } from "@/components/classification-chip-row";
import { FilterConfig } from "@/types/filters";
import { SiteHeader } from "@/components/site-header";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const POSTS_PER_PAGE = 20;

function NotesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Get search and page from URL
  const searchQuery = searchParams.get("search") || "";
  const currentPage = parseInt(searchParams.get("page") || "1", 10);
  const page = Math.max(0, currentPage - 1); // Convert to 0-based for API
  const offset = page * POSTS_PER_PAGE;

  // Parse filters from URL
  const filtersParam = searchParams.get("filters");
  const [filters, setFilters] = useState<FilterConfig>(() => {
    if (filtersParam) {
      try {
        return JSON.parse(decodeURIComponent(filtersParam));
      } catch {
        return {};
      }
    }
    return {};
  });

  // Local state for search input (for immediate UI feedback)
  const [searchInput, setSearchInput] = useState(searchQuery);
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false);

  const {
    data: postsData,
    isLoading,
    error,
    isFetching,
  } = usePublicPosts(POSTS_PER_PAGE, offset, searchQuery, filters);

  const totalPages = postsData
    ? Math.ceil(postsData.total / POSTS_PER_PAGE)
    : 0;

  // Sync local search input with URL when URL changes
  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);

  // Function to update URL with search, page, and filter parameters
  const updateUrl = (
    newSearch: string = searchQuery,
    newPage: number = 0,
    newFilters: FilterConfig = filters
  ) => {
    const params = new URLSearchParams();

    if (newSearch.trim()) {
      params.set("search", newSearch.trim());
    }

    const userPageNumber = newPage + 1;
    if (userPageNumber > 1) {
      params.set("page", userPageNumber.toString());
    }

    if (Object.keys(newFilters).length > 0) {
      params.set("filters", encodeURIComponent(JSON.stringify(newFilters)));
    }

    const newUrl = params.toString() ? `/posts?${params.toString()}` : "/posts";
    router.push(newUrl);
  };

  // Function to navigate to a specific page
  const navigateToPage = (newPage: number) => {
    updateUrl(searchQuery, newPage, filters);
  };

  // Function to perform search
  const handleSearch = () => {
    updateUrl(searchInput, 0, filters); // Reset to first page when searching
  };

  // Function to clear search
  const clearSearch = () => {
    setSearchInput("");
    updateUrl("", 0, filters);
  };

  // Function to handle filter changes
  const handleFiltersChange = (newFilters: FilterConfig) => {
    setFilters(newFilters);
    updateUrl(searchQuery, 0, newFilters); // Reset to first page when filtering
    setIsFilterPanelOpen(false); // Close panel on mobile after applying
  };

  // Count active filters
  const activeFilterCount = Object.keys(filters).reduce((count, slug) => {
    const filter = filters[slug];
    let filterCount = 0;
    if (filter.has_classification) filterCount++;
    if (filter.values?.length) filterCount += filter.values.length;
    if (filter.hierarchy?.level1) filterCount++;
    if (filter.hierarchy?.level2) filterCount++;
    return count + filterCount;
  }, 0);

  // Handle Enter key in search input
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  // Only show full page skeleton on initial load
  if (isLoading && !postsData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Error Loading Posts
            </h1>
            <p className="text-gray-600">
              Failed to load posts. Please try again later.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />

      {/* Page Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-gray-600 mt-2">
                Browse posts from X.com that have received requests for a
                Community Note • {postsData?.total || 0}
                {searchQuery ? ` results for "${searchQuery}"` : " posts total"}
                {activeFilterCount > 0 &&
                  ` • ${activeFilterCount} filters active`}
              </p>
            </div>
          </div>

          {/* Search and Filter Controls */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                type="text"
                placeholder="Search posts..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                className="pl-10 pr-10"
              />
              {searchInput && (
                <button
                  onClick={clearSearch}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <Button onClick={handleSearch} size="sm" disabled={isFetching}>
              Search
            </Button>
            {searchQuery && (
              <Button
                onClick={clearSearch}
                variant="outline"
                size="sm"
                disabled={isFetching}
              >
                Clear
              </Button>
            )}

            {/* Mobile Filter Button */}
            <div className="lg:hidden">
              <Sheet
                open={isFilterPanelOpen}
                onOpenChange={setIsFilterPanelOpen}
              >
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="h-4 w-4 mr-2" />
                    Filters
                    {activeFilterCount > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {activeFilterCount}
                      </Badge>
                    )}
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-full sm:w-96 p-0">
                  <SheetHeader className="p-4 border-b">
                    <SheetTitle>Classification Filters</SheetTitle>
                    <SheetDescription>
                      Filter posts by their classifications
                    </SheetDescription>
                  </SheetHeader>
                  <ClassificationFilterPanel
                    currentFilters={filters}
                    onFiltersChange={handleFiltersChange}
                    className="border-0 shadow-none rounded-none"
                  />
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex gap-6">
          {/* Desktop Filter Sidebar */}
          <div className="hidden lg:block w-80 flex-shrink-0">
            <div className="sticky top-4">
              <ClassificationFilterPanel
                currentFilters={filters}
                onFiltersChange={handleFiltersChange}
              />
            </div>
          </div>

          {/* Posts List */}
          <div className="flex-1">
            {/* Loading indicator at the top for subsequent fetches */}
            {isFetching && (
              <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-center">
                <div className="flex items-center gap-3">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                  <p className="text-blue-700 font-medium">Loading posts...</p>
                </div>
              </div>
            )}

            {postsData?.posts.length === 0 ? (
              <div className="text-center py-12">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  {searchQuery ? "No matching posts found" : "No posts found"}
                </h2>
                <p className="text-gray-600">
                  {searchQuery
                    ? `No posts match your search for "${searchQuery}". Try different keywords.`
                    : "No posts have been ingested yet."}
                </p>
                {searchQuery && (
                  <Button
                    onClick={clearSearch}
                    variant="outline"
                    className="mt-4"
                  >
                    Clear search
                  </Button>
                )}
              </div>
            ) : (
              <div
                className={`space-y-6 transition-opacity duration-200 ${
                  isFetching ? "opacity-50" : "opacity-100"
                }`}
              >
                {postsData?.posts.map((post) => (
                  <Card
                    key={post.post_uid}
                    className="hover:shadow-md transition-shadow cursor-pointer group relative"
                  >
                    <Link
                      href={`/posts/${encodeURIComponent(post.post_uid)}${
                        searchParams.toString() ? `?${searchParams.toString()}` : ""
                      }`}
                      className="block"
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <CardTitle className="text-lg group-hover:text-blue-600 transition-colors">
                              {post.author_handle
                                ? `@${post.author_handle}`
                                : "Anonymous"}
                            </CardTitle>
                            <CardDescription className="flex items-center gap-2 mt-1">
                              <span>{post.platform.toUpperCase()}</span>
                              <span>•</span>
                              <span>
                                {post.created_at
                                  ? new Date(
                                      post.created_at
                                    ).toLocaleDateString()
                                  : new Date(
                                      post.ingested_at
                                    ).toLocaleDateString()}
                              </span>
                              {post.topic_display_name && (
                                <>
                                  <span>•</span>
                                  <Badge variant="secondary">
                                    {post.topic_display_name}
                                  </Badge>
                                </>
                              )}
                            </CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            {post.has_note && (
                              <Badge
                                variant={
                                  post.submission_status === "accepted"
                                    ? "default"
                                    : "outline"
                                }
                              >
                                {post.submission_status === "accepted"
                                  ? "Accepted Note"
                                  : "Submitted Note"}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-gray-900 mb-3 line-clamp-3">
                          {post.text}
                        </p>
                        {post.classifications &&
                          post.classifications.length > 0 && (
                            <ClassificationChipRow
                              classifications={post.classifications}
                              className="mb-3"
                            />
                          )}
                        <div className="flex justify-between items-center">
                          <span className="text-blue-600 group-hover:text-blue-800 font-medium transition-colors">
                            View Details →
                          </span>
                          {!post.has_note && (
                            <span className="text-sm text-gray-500">
                              Fact-check pending
                            </span>
                          )}
                        </div>
                      </CardContent>
                    </Link>
                    {/* External link positioned absolutely to avoid nesting */}
                    <a
                      href={`https://x.com/i/web/status/${post.platform_post_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 z-10"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </Card>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-8">
                <Button
                  variant="outline"
                  onClick={() => navigateToPage(Math.max(0, page - 1))}
                  disabled={page === 0 || isFetching}
                  className="flex items-center gap-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </Button>

                <span className="text-sm text-gray-600">
                  Page {page + 1} of {totalPages}
                </span>

                <Button
                  variant="outline"
                  onClick={() =>
                    navigateToPage(Math.min(totalPages - 1, page + 1))
                  }
                  disabled={page === totalPages - 1 || isFetching}
                  className="flex items-center gap-2"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NotesPage() {
  return (
    <Suspense fallback={<div className="flex justify-center items-center min-h-screen">Loading...</div>}>
      <NotesPageContent />
    </Suspense>
  );
}
