/**
 * Utilities for Twitter/X character counting
 */

// URL regex pattern - simplified version that matches most URLs
const URL_REGEX = /https?:\/\/[^\s]+|www\.[^\s]+/gi;

/**
 * Count characters for Twitter/X, where URLs count as 1 character each
 * @param text The text to count
 * @returns The character count for Twitter
 */
export function countTwitterCharacters(text: string): number {
  // Replace all URLs with a single character placeholder
  const textWithUrlsReplaced = text.replace(URL_REGEX, "U");
  // 15 is for the "More Details: {link}" text
  return textWithUrlsReplaced.length + 15;
}

/**
 * Check if text is within Twitter's 280 character limit
 * @param text The text to check
 * @returns True if within limit
 */
export function isWithinTwitterLimit(text: string): boolean {
  return countTwitterCharacters(text) <= 280;
}

/**
 * Get remaining characters for Twitter
 * @param text The current text
 * @returns Number of characters remaining (can be negative)
 */
export function getRemainingCharacters(text: string): number {
  return 280 - countTwitterCharacters(text);
}
