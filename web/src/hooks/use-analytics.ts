import {
  trackPageView,
  trackPostViewed,
  trackSearchPerformed,
  trackOutboundLinkClicked,
} from "@/lib/mixpanel";

export const useAnalytics = () => {
  return {
    trackPageView,
    trackPostViewed,
    trackSearchPerformed,
    trackOutboundLinkClicked,
  };
};