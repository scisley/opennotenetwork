export enum AnalyticsEvent {
  PAGE_VIEWED = "Page Viewed",
  POST_VIEWED = "Post Viewed",
  SEARCH_PERFORMED = "Search Performed",
  OUTBOUND_LINK_CLICKED = "Outbound Link Clicked",
}

export interface PageViewedProps {
  page: string; // pathname
  url: string; // full URL
  referrer?: string; // document.referrer
}

export interface PostViewedProps {
  post_uid: string;
  has_fact_check: boolean;
  has_note: boolean;
  has_submitted_note: boolean;
}

export interface SearchPerformedProps {
  query: string;
  page: number;
  filters: string[];
  results_count: number;
}

export interface OutboundLinkClickedProps {
  url_domain: string;
  url: string;
  context: "fact_check" | "note" | "footer";
}