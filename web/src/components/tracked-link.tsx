"use client";

import { useAnalytics } from "@/hooks/use-analytics";
import { ReactNode } from "react";

interface TrackedLinkProps {
  href: string;
  context: "fact_check" | "note" | "footer";
  children: ReactNode;
  className?: string;
  target?: string;
  rel?: string;
}

export function TrackedLink({
  href,
  context,
  children,
  className,
  target = "_blank",
  rel = "noopener noreferrer",
}: TrackedLinkProps) {
  const { trackOutboundLinkClicked } = useAnalytics();

  const handleClick = () => {
    // Extract domain from URL
    try {
      const url = new URL(href);
      const domain = url.hostname.replace("www.", "");

      trackOutboundLinkClicked({
        url_domain: domain,
        url: href,
        context: context,
      });
    } catch {
      // If URL parsing fails, still track with raw href
      trackOutboundLinkClicked({
        url_domain: "unknown",
        url: href,
        context: context,
      });
    }
  };

  return (
    <a
      href={href}
      target={target}
      rel={rel}
      className={className}
      onClick={handleClick}
    >
      {children}
    </a>
  );
}
