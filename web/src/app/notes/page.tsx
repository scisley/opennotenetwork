'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { usePublicPosts } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChevronLeft, ChevronRight, ExternalLink, Search, X } from 'lucide-react';

const POSTS_PER_PAGE = 20;

export default function NotesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Get search and page from URL
  const searchQuery = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const page = Math.max(0, currentPage - 1); // Convert to 0-based for API
  const offset = page * POSTS_PER_PAGE;
  
  // Local state for search input (for immediate UI feedback)
  const [searchInput, setSearchInput] = useState(searchQuery);
  
  const { data: postsData, isLoading, error } = usePublicPosts(POSTS_PER_PAGE, offset, searchQuery);
  
  const totalPages = postsData ? Math.ceil(postsData.total / POSTS_PER_PAGE) : 0;
  
  // Sync local search input with URL when URL changes
  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);
  
  // Function to update URL with search and page parameters
  const updateUrl = (newSearch: string = searchQuery, newPage: number = 0) => {
    const params = new URLSearchParams();
    
    if (newSearch.trim()) {
      params.set('search', newSearch.trim());
    }
    
    const userPageNumber = newPage + 1;
    if (userPageNumber > 1) {
      params.set('page', userPageNumber.toString());
    }
    
    const newUrl = params.toString() ? `/notes?${params.toString()}` : '/notes';
    router.push(newUrl);
  };
  
  // Function to navigate to a specific page
  const navigateToPage = (newPage: number) => {
    updateUrl(searchQuery, newPage);
  };
  
  // Function to perform search
  const handleSearch = () => {
    updateUrl(searchInput, 0); // Reset to first page when searching
  };
  
  // Function to clear search
  const clearSearch = () => {
    setSearchInput('');
    updateUrl('', 0);
  };
  
  // Handle Enter key in search input
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };
  
  if (isLoading) {
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
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Error Loading Posts</h1>
            <p className="text-gray-600">Failed to load posts. Please try again later.</p>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Climate Posts</h1>
              <p className="text-gray-600 mt-2">
                Browse posts from X.com Community Notes • {postsData?.total || 0} 
                {searchQuery ? ` results for "${searchQuery}"` : ' posts total'}
              </p>
            </div>
            <Link href="/" className="text-blue-600 hover:text-blue-800">
              ← Back to Home
            </Link>
          </div>
          
          {/* Search Box */}
          <div className="flex items-center gap-2 max-w-md">
            <div className="relative flex-1">
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
            <Button onClick={handleSearch} size="sm">
              Search
            </Button>
            {searchQuery && (
              <Button onClick={clearSearch} variant="outline" size="sm">
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Posts List */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {postsData?.posts.length === 0 ? (
          <div className="text-center py-12">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {searchQuery ? 'No matching posts found' : 'No posts found'}
            </h2>
            <p className="text-gray-600">
              {searchQuery 
                ? `No posts match your search for "${searchQuery}". Try different keywords.`
                : 'No posts have been ingested yet.'
              }
            </p>
            {searchQuery && (
              <Button onClick={clearSearch} variant="outline" className="mt-4">
                Clear search
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {postsData?.posts.map((post) => (
              <Card 
                key={post.post_uid} 
                className="hover:shadow-md transition-shadow cursor-pointer group"
                onClick={() => router.push(`/notes/${encodeURIComponent(post.post_uid)}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg group-hover:text-blue-600 transition-colors">
                        {post.author_handle ? `@${post.author_handle}` : 'Anonymous'}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <span>{post.platform.toUpperCase()}</span>
                        <span>•</span>
                        <span>
                          {post.created_at
                            ? new Date(post.created_at).toLocaleDateString()
                            : new Date(post.ingested_at).toLocaleDateString()}
                        </span>
                        {post.topic_display_name && (
                          <>
                            <span>•</span>
                            <Badge variant="secondary">{post.topic_display_name}</Badge>
                          </>
                        )}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {post.has_note && (
                        <Badge variant={
                          post.submission_status === 'accepted' ? 'default' : 'outline'
                        }>
                          {post.submission_status === 'accepted' ? 'Accepted Note' : 'Submitted Note'}
                        </Badge>
                      )}
                      <Link
                        href={`https://x.com/i/web/status/${post.platform_post_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-gray-600 z-10 relative"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-900 mb-4 line-clamp-3">
                    {post.text}
                  </p>
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
              disabled={page === 0}
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
              onClick={() => navigateToPage(Math.min(totalPages - 1, page + 1))}
              disabled={page === totalPages - 1}
              className="flex items-center gap-2"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}