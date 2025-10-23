"use client";

import { useEffect, useRef, useState } from "react";

interface TwitterEmbedProps {
  postId: string;
  author?: string;
  className?: string;
  defaultCollapsed?: boolean;
}

declare global {
  interface Window {
    twttr?: {
      widgets?: {
        load?: (element?: HTMLElement) => void;
        createTweet?: (
          id: string,
          element: HTMLElement,
          options?: any
        ) => Promise<HTMLElement | undefined>;
      };
    };
  }
}

export function TwitterEmbed({
  postId,
  className = "",
  defaultCollapsed = true,
}: TwitterEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  useEffect(() => {
    const loadTwitterScript = () => {
      return new Promise<void>((resolve) => {
        // Check if script is already loaded
        if (window.twttr && window.twttr.widgets) {
          resolve();
          return;
        }

        // Check if script is already in head to avoid duplicates
        const existingScript = document.querySelector(
          'script[src="https://platform.twitter.com/widgets.js"]'
        );
        if (existingScript) {
          // Wait for existing script to load
          const checkLoaded = () => {
            if (window.twttr && window.twttr.widgets) {
              resolve();
            } else {
              setTimeout(checkLoaded, 100);
            }
          };
          checkLoaded();
          return;
        }

        // Create and load the script
        const script = document.createElement("script");
        script.src = "https://platform.twitter.com/widgets.js";
        script.async = true;
        script.charset = "utf-8";
        script.onload = () => resolve();
        script.onerror = () => resolve(); // Continue even if script fails
        document.head.appendChild(script);
      });
    };

    const createEmbed = async () => {
      if (!containerRef.current) return;

      try {
        // Clear container first
        containerRef.current.innerHTML = "";

        await loadTwitterScript();

        if (window.twttr?.widgets?.createTweet) {
          // Create a unique container div
          const embedContainer = document.createElement("div");
          containerRef.current.appendChild(embedContainer);

          const result = await window.twttr.widgets.createTweet(
            postId,
            embedContainer,
            {
              theme: "light",
              // conversation: "none",
              cards: "visible",
              dnt: true,
            }
          );

          if (!result) {
            throw new Error("Failed to create tweet embed");
          }
        } else {
          throw new Error("Twitter widgets not available");
        }
      } catch (error) {
        console.error("Failed to load Twitter embed:", error);

        // Fallback content
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <div class="border border-gray-200 rounded-lg p-4 bg-gray-50 text-center">
              <p class="text-gray-600 mb-2">Twitter embed unavailable</p>
              <a 
                href="https://x.com/i/web/status/${postId}" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-blue-600 hover:text-blue-800 font-medium"
              >
                View on X.com →
              </a>
            </div>
          `;
        }
      }
    };

    // Add a small delay to ensure DOM is ready
    const timeoutId = setTimeout(createEmbed, 100);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [postId]);

  return (
    <div className={`twitter-embed-container ${className} relative`}>
      <div
        ref={containerRef}
        className={`min-h-[200px] [&>div]:w-full [&_iframe]:!max-w-[550px] [&_iframe]:!w-full [&_iframe]:!-mt-2.5 transition-all duration-300 ${
          isCollapsed ? "max-h-[350px] overflow-hidden" : ""
        }`}
      >
        <div className="animate-pulse flex items-center justify-center min-h-[200px]">
          <div className="h-32 bg-gray-200 rounded w-full"></div>
        </div>
      </div>

      {/* Gradient overlay and See more button when collapsed */}
      {isCollapsed && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white/95 to-transparent pt-16">
          <button
            onClick={() => setIsCollapsed(false)}
            className="w-full py-3 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            See more
          </button>
        </div>
      )}

      {/* Show less button when expanded */}
      {!isCollapsed && (
        <div className="mt-2">
          <button
            onClick={() => setIsCollapsed(true)}
            className="w-full py-3 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            Show less
          </button>
        </div>
      )}
    </div>
  );
}
