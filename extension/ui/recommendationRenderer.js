/**
 * Recommendation Renderer Module
 *
 * Provides UI rendering functions for recommendations.
 * Consolidates duplicate rendering logic from multiple files.
 */

import { AI_SUGGESTION_MARKER } from "./constants.js";

/**
 * Create a single recommendation list item element
 *
 * @param {{query: string, reason: string}} recommendation - Recommendation object
 * @param {Object} options - Rendering options
 * @param {boolean} options.enableClick - Whether to attach click handler (default: true)
 * @returns {HTMLLIElement} The created list item element
 */
export function renderRecommendationItem(recommendation, options = {}) {
  const { enableClick = true } = options;

  const li = document.createElement("li");

  // Detect AI suggestion and add special styling
  const isAISuggestion = recommendation.reason && recommendation.reason.includes(AI_SUGGESTION_MARKER);
  if (isAISuggestion) {
    li.classList.add("ai-suggestion");
  }

  // Create inner HTML structure
  li.innerHTML = `
    <span class="query-text">${recommendation.query}</span>
    <span class="query-reason">${recommendation.reason}</span>
  `;

  // Attach click handler to open Google search
  if (enableClick) {
    li.addEventListener("click", () => {
      window.open(
        `https://www.google.com/search?q=${encodeURIComponent(recommendation.query)}`,
        "_blank"
      );
    });
  }

  return li;
}

/**
 * Render a list of recommendations into a container element
 *
 * @param {HTMLElement} listElement - The UL element to render recommendations into
 * @param {Array<{query: string, reason: string}>} recommendations - Array of recommendations
 * @param {Object} options - Rendering options
 * @param {boolean} options.clearExisting - Whether to clear existing content (default: true)
 * @param {boolean} options.enableClick - Whether to enable click handlers (default: true)
 */
export function renderRecommendationList(listElement, recommendations, options = {}) {
  const { clearExisting = true, enableClick = true } = options;

  // Clear existing content if requested
  if (clearExisting) {
    listElement.innerHTML = "";
  }

  // Render each recommendation
  recommendations.forEach((recommendation) => {
    const li = renderRecommendationItem(recommendation, { enableClick });
    listElement.appendChild(li);
  });
}

/**
 * Render recommendation history with time separators
 *
 * @param {HTMLElement} listElement - The UL element to render history into
 * @param {Array<{timestamp: string, timeString: string, recommendations: Array}>} historyEntries - Array of history entries
 * @param {Object} options - Rendering options
 * @param {boolean} options.clearExisting - Whether to clear existing content (default: true)
 * @param {boolean} options.newestFirst - Whether to show newest entries first (default: true)
 */
export function renderHistorySection(listElement, historyEntries, options = {}) {
  const { clearExisting = true, newestFirst = true } = options;

  // Clear existing content if requested
  if (clearExisting) {
    listElement.innerHTML = "";
  }

  // Sort entries if needed (newest first by default)
  const entries = newestFirst
    ? [...historyEntries].reverse()
    : historyEntries;

  // Render each history entry with time separator
  entries.forEach((entry) => {
    // Create time separator
    const separator = createTimestampSeparator(entry.timeString);
    listElement.appendChild(separator);

    // Render recommendation items
    entry.recommendations.forEach((recommendation) => {
      const li = renderRecommendationItem(recommendation, { enableClick: true });
      listElement.appendChild(li);
    });
  });
}

/**
 * Create a timestamp separator element
 *
 * @param {string} timeString - Formatted time string (e.g., "14:30")
 * @returns {HTMLDivElement} The separator element
 */
function createTimestampSeparator(timeString) {
  const separator = document.createElement("div");
  separator.className = "recommendation-separator";
  separator.textContent = `${timeString} の推薦`;
  return separator;
}

/**
 * Extract recommendation data from a list element's DOM
 *
 * @param {HTMLElement} listElement - The UL element containing recommendation items
 * @returns {Array<{query: string, reason: string}>} Array of extracted recommendations
 */
export function extractRecommendationsFromList(listElement) {
  const recommendations = [];

  Array.from(listElement.children).forEach((child) => {
    const queryText = child.querySelector(".query-text")?.textContent;
    const queryReason = child.querySelector(".query-reason")?.textContent;

    if (queryText && queryReason) {
      recommendations.push({
        query: queryText,
        reason: queryReason
      });
    }
  });

  return recommendations;
}
