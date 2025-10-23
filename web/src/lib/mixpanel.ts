import mixpanel from "mixpanel-browser";
import {
  AnalyticsEvent,
  PageViewedProps,
  PostViewedProps,
  SearchPerformedProps,
  OutboundLinkClickedProps,
} from "./analytics-events";

const isAnalyticsEnabled = () => {
  const enabled = process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === "true";
  return enabled;
};

const isInitialized = () => {
  return isAnalyticsEnabled() && typeof window !== "undefined";
};

export const initMixpanel = () => {
  if (!isAnalyticsEnabled()) {
    return;
  }

  const token = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
  if (!token) {
    console.warn("Mixpanel token is missing");
    return;
  }

  if (typeof window === "undefined") {
    return;
  }

  try {
    mixpanel.init(token, {
      debug: false, // Set to true for debugging
      track_pageview: false, // We'll track this manually
      persistence: "localStorage",
      ignore_dnt: true, // Ignore Do Not Track browser setting
    });
  } catch (error) {
    console.error("Failed to initialize Mixpanel:", error);
  }
};

export const track = (
  event: AnalyticsEvent,
  properties?:
    | PageViewedProps
    | PostViewedProps
    | SearchPerformedProps
    | OutboundLinkClickedProps
) => {
  if (!isInitialized()) {
    return;
  }

  try {
    mixpanel.track(event, properties);
  } catch (error) {
    console.error("Failed to track event:", event, error);
  }
};

export const trackPageView = (props: PageViewedProps) => {
  track(AnalyticsEvent.PAGE_VIEWED, props);
};

export const trackPostViewed = (props: PostViewedProps) => {
  track(AnalyticsEvent.POST_VIEWED, props);
};

export const trackSearchPerformed = (props: SearchPerformedProps) => {
  track(AnalyticsEvent.SEARCH_PERFORMED, props);
};

export const trackOutboundLinkClicked = (props: OutboundLinkClickedProps) => {
  track(AnalyticsEvent.OUTBOUND_LINK_CLICKED, props);
};