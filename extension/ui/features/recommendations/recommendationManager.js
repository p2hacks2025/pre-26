/**
 * Recommendation Manager Module
 *
 * Manages business logic for recommendations.
 * Coordinates between storage and rendering layers.
 */

import { saveRecommendationHistory, loadRecommendationHistory, clearRecommendationHistory } from "./recommendationStorage.js";
import { renderRecommendationList, renderHistorySection, extractRecommendationsFromList } from "./recommendationRenderer.js";
import { AI_SUGGESTION_LABEL } from "../../core/constants.js";

/**
 * Archive current recommendations to history
 *
 * Moves recommendations from the current list to the previous recommendations list
 * and saves them to localStorage for persistence.
 *
 * @param {HTMLElement} currentListElement - The current recommendation list element
 * @param {HTMLElement} previousListElement - The previous recommendations list element
 * @param {HTMLElement} previousSectionElement - The previous recommendations section element
 * @returns {Promise<boolean>} True if archiving was successful
 */
export async function archiveCurrentRecommendations(
  currentListElement,
  previousListElement,
  previousSectionElement
) {
  try {
    // Check if there are recommendations to archive
    if (currentListElement.children.length === 0) {
      return false;
    }

    // Extract current recommendations data
    const currentRecommendations = extractRecommendationsFromList(currentListElement);

    // Create timestamp
    const now = new Date();
    const timeString = now.toLocaleTimeString("ja-JP", {
      hour: "2-digit",
      minute: "2-digit"
    });

    // Save to localStorage
    const saved = saveRecommendationHistory(currentRecommendations, timeString);

    if (saved) {
      // Create timestamp separator
      const separator = document.createElement("div");
      separator.className = "recommendation-separator";
      separator.textContent = `${timeString} の推薦`;

      // Insert separator at the beginning (newest first)
      previousListElement.insertBefore(separator, previousListElement.firstChild);

      // Clone and insert recommendation items
      Array.from(currentListElement.children)
        .reverse()
        .forEach((child) => {
          const clonedChild = child.cloneNode(true);
          previousListElement.insertBefore(clonedChild, previousListElement.firstChild);
        });

      // Show the previous recommendations section
      previousSectionElement.style.display = "block";
    }

    return saved;
  } catch (error) {
    console.error("Failed to archive current recommendations:", error);
    return false;
  }
}

/**
 * Restore recommendation history from localStorage to the UI
 *
 * @param {HTMLElement} listElement - The list element to render history into
 * @param {HTMLElement} sectionElement - The section element to show/hide
 * @returns {boolean} True if restoration was successful
 */
export function restoreRecommendationHistory(listElement, sectionElement) {
  try {
    const history = loadRecommendationHistory();

    if (history.length === 0) {
      return false;
    }

    // Render history with the renderer module
    renderHistorySection(listElement, history, {
      clearExisting: true,
      newestFirst: true
    });

    // Show the section
    sectionElement.style.display = "block";

    return true;
  } catch (error) {
    console.error("Failed to restore recommendation history:", error);
    return false;
  }
}

/**
 * Format AI suggestion search queries into recommendation objects
 *
 * @param {Array<string>} searchQueries - Array of search query strings
 * @returns {Array<{query: string, reason: string}>} Formatted recommendation objects
 */
export function formatAISuggestions(searchQueries) {
  return searchQueries.map((query) => ({
    query: query,
    reason: AI_SUGGESTION_LABEL
  }));
}

/**
 * Clear all recommendations from UI and storage
 *
 * @param {HTMLElement} currentListElement - The current recommendation list element
 * @param {HTMLElement} previousListElement - The previous recommendations list element
 * @param {HTMLElement} previousSectionElement - The previous recommendations section element
 * @returns {boolean} True if clearing was successful
 */
export function clearAllRecommendations(
  currentListElement,
  previousListElement,
  previousSectionElement
) {
  try {
    // Clear DOM elements
    if (currentListElement) {
      currentListElement.innerHTML = "";
    }

    if (previousListElement) {
      previousListElement.innerHTML = "";
    }

    if (previousSectionElement) {
      previousSectionElement.style.display = "none";
    }

    // Clear localStorage
    clearRecommendationHistory();

    return true;
  } catch (error) {
    console.error("Failed to clear all recommendations:", error);
    return false;
  }
}
