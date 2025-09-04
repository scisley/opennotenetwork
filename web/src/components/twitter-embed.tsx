"use client";

import { useEffect, useRef } from "react";

interface TwitterEmbedProps {
  postId: string;
  author?: string;
  className?: string;
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

export function TwitterEmbed({ postId, className = "" }: TwitterEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null);

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
    <div className={`twitter-embed-container ${className}`}>
      <div
        ref={containerRef}
        className="min-h-[200px] flex items-center justify-center [&>div]:w-full [&_iframe]:!max-w-[550px] [&_iframe]:!w-full"
      >
        <div className="animate-pulse">
          <div className="h-32 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    </div>
  );
}
