"use client";

import { useEffect, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { initMixpanel, trackPageView } from "@/lib/mixpanel";

// Separate component for tracking that uses useSearchParams
function MixpanelTracking() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Track page views on route change
  useEffect(() => {
    if (typeof window === "undefined") return;

    const url = window.location.href;
    const referrer = document.referrer || undefined;

    trackPageView({
      page: pathname,
      url: url,
      referrer: referrer,
    });
  }, [pathname, searchParams]);

  return null;
}

export function MixpanelProvider({ children }: { children: React.ReactNode }) {
  // Initialize Mixpanel on mount
  useEffect(() => {
    initMixpanel();
  }, []);

  return (
    <>
      <Suspense fallback={null}>
        <MixpanelTracking />
      </Suspense>
      {children}
    </>
  );
}