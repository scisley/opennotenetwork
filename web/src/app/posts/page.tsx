"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { usePublicPosts } from "@/hooks/use-api";
import { PostWidget } from "@/components/post-widget";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  X,
  Filter,
} from "lucide-react";
import {
  ClassificationFilterPanel,
  StatusFilters
} from "@/components/filters/classification-filter-panel";
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
import { useAnalytics } from "@/hooks/use-analytics";

const POSTS_PER_PAGE = 20;

function NotesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { trackSearchPerformed } = useAnalytics();

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

  // Parse status filters from URL
  const statusFiltersParam = searchParams.get("statusFilters");
  const [statusFilters, setStatusFilters] = useState<StatusFilters>(() => {
    if (statusFiltersParam) {
      try {
        return JSON.parse(decodeURIComponent(statusFiltersParam));
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
  } = usePublicPosts(
    POSTS_PER_PAGE,
    offset,
    searchQuery,
    filters,
    statusFilters.hasFactCheck,
    statusFilters.hasNote,
    statusFilters.factCheckStatus,
    statusFilters.noteStatus,
    statusFilters.dateRange?.after,
    statusFilters.dateRange?.before
  );

  const totalPages = postsData
    ? Math.ceil(postsData.total / POSTS_PER_PAGE)
    : 0;

  // Sync local search input with URL when URL changes
  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);

  // Track search when results are loaded
  useEffect(() => {
    // Only track when we have data and we're not currently fetching
    // This prevents duplicate events from stale data
    if (postsData && !isFetching) {
      // Collect active filter keys
      const activeFilterKeys: string[] = [];

      // Add classification filters
      Object.keys(filters).forEach((slug) => {
        const filter = filters[slug];
        if (filter.has_classification) {
          activeFilterKeys.push(`${slug}_has_classification`);
        }
        if (filter.values?.length) {
          filter.values.forEach((value) => {
            activeFilterKeys.push(`${slug}_${value}`);
          });
        }
        if (filter.hierarchy?.level1) {
          activeFilterKeys.push(`${slug}_${filter.hierarchy.level1}`);
        }
        if (filter.hierarchy?.level2) {
          activeFilterKeys.push(`${slug}_${filter.hierarchy.level2}`);
        }
      });

      // Add status filters
      if (statusFilters.hasFactCheck) {
        activeFilterKeys.push("has_fact_check");
      }
      if (statusFilters.hasNote) {
        activeFilterKeys.push("has_note");
      }

      trackSearchPerformed({
        query: searchQuery || "",
        page: currentPage,
        filters: activeFilterKeys,
        results_count: postsData.total,
      });
    }
  }, [postsData, isFetching, searchQuery, currentPage, filters, statusFilters, trackSearchPerformed]);

  // Function to update URL with search, page, and filter parameters
  const updateUrl = (
    newSearch: string = searchQuery,
    newPage: number = 0,
    newFilters: FilterConfig = filters,
    newStatusFilters: StatusFilters = statusFilters
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

    if (Object.keys(newStatusFilters).length > 0) {
      params.set("statusFilters", encodeURIComponent(JSON.stringify(newStatusFilters)));
    }

    const newUrl = params.toString() ? `/posts?${params.toString()}` : "/posts";
    router.push(newUrl);
  };

  // Function to navigate to a specific page
  const navigateToPage = (newPage: number) => {
    updateUrl(searchQuery, newPage, filters, statusFilters);
  };

  // Function to perform search
  const handleSearch = () => {
    updateUrl(searchInput, 0, filters, statusFilters); // Reset to first page when searching
  };

  // Function to clear search
  const clearSearch = () => {
    setSearchInput("");
    updateUrl("", 0, filters, statusFilters);
  };

  // Function to handle filter changes
  const handleFiltersChange = (newFilters: FilterConfig) => {
    setFilters(newFilters);
    updateUrl(searchQuery, 0, newFilters, statusFilters); // Reset to first page when filtering
    setIsFilterPanelOpen(false); // Close panel on mobile after applying
  };

  // Function to handle status filter changes
  const handleStatusFiltersChange = (newStatusFilters: StatusFilters) => {
    setStatusFilters(newStatusFilters);
    updateUrl(searchQuery, 0, filters, newStatusFilters); // Reset to first page when filtering
    setIsFilterPanelOpen(false); // Close panel on mobile after applying
  };

  // Function to handle both filters at once (for Apply/Clear operations)
  const handleBothFiltersChange = (newFilters: FilterConfig, newStatusFilters: StatusFilters) => {
    setFilters(newFilters);
    setStatusFilters(newStatusFilters);
    updateUrl(searchQuery, 0, newFilters, newStatusFilters); // Reset to first page when filtering
    setIsFilterPanelOpen(false); // Close panel on mobile after applying
  };

  // Count active filters - only count actual selected values
  const activeFilterCount = Object.keys(filters).reduce((count, slug) => {
    const filter = filters[slug];
    let filterCount = 0;
    // Only count actual selected values, not just "has_classification"
    if (filter.values?.length) filterCount += filter.values.length;
    if (filter.hierarchy?.level1) filterCount++;
    if (filter.hierarchy?.level2) filterCount++;
    return count + filterCount;
  }, 0) +
  (statusFilters.hasFactCheck ? 1 : 0) +
  (statusFilters.hasNote ? 1 : 0) +
  (statusFilters.factCheckStatus ? 1 : 0) +
  (statusFilters.noteStatus ? 1 : 0) +
  (statusFilters.dateRange?.after || statusFilters.dateRange?.before ? 1 : 0);

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
            <div className="relative flex-1 max-w-2xl">
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

            {/* Unified Filter Button - For all screen sizes */}
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
              <SheetContent side="left" className="w-full sm:w-96 p-0 flex flex-col h-full">
                <SheetHeader className="p-4 border-b flex-shrink-0">
                  <SheetTitle>Filters</SheetTitle>
                  <SheetDescription>
                    Filter posts by status and classifications
                  </SheetDescription>
                </SheetHeader>
                <div className="flex-1 overflow-hidden">
                  <ClassificationFilterPanel
                    currentFilters={filters}
                    onFiltersChange={handleFiltersChange}
                    currentStatusFilters={statusFilters}
                    onStatusFiltersChange={handleStatusFiltersChange}
                    onBothFiltersChange={handleBothFiltersChange}
                    className="border-0 shadow-none rounded-none h-full"
                  />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Posts List - Now full width */}
        <div className="w-full">
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
                className={`grid gap-4 transition-opacity duration-200 ${
                  isFetching ? "opacity-50" : "opacity-100"
                } grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`}
              >
                {postsData?.posts.map((post) => (
                  <PostWidget
                    key={post.post_uid}
                    post={post}
                    href={`/posts/${encodeURIComponent(post.post_uid)}${
                      searchParams.toString() ? `?${searchParams.toString()}` : ""
                    }`}
                  />
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
  );
}

export default function NotesPage() {
  return (
    <Suspense fallback={<div className="flex justify-center items-center min-h-screen">Loading...</div>}>
      <NotesPageContent />
    </Suspense>
  );
}
