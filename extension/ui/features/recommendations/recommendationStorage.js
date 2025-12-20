/**
 * Recommendation History Storage Module
 *
 * Manages localStorage operations for recommendation history.
 * Provides centralized access to recommendation history persistence.
 */

import { RECOMMENDATION_HISTORY_KEY, MAX_RECOMMENDATION_HISTORY } from "../../core/constants.js";

/**
 * Save a new recommendation entry to localStorage history
 *
 * @param {Array<{query: string, reason: string}>} recommendations - Array of recommendation objects
 * @param {string} timeString - Formatted time string (e.g., "14:30")
 * @returns {boolean} True if save was successful, false otherwise
 */
export function saveRecommendationHistory(recommendations, timeString) {
  try {
    const history = loadRecommendationHistory();
    const newEntry = {
      timestamp: new Date().toISOString(),
      timeString: timeString,
      recommendations: recommendations
    };

    // Add new entry at the beginning (newest first)
    history.unshift(newEntry);

    // Maintain maximum history limit
    if (history.length > MAX_RECOMMENDATION_HISTORY) {
      history.splice(MAX_RECOMMENDATION_HISTORY);
    }

    localStorage.setItem(RECOMMENDATION_HISTORY_KEY, JSON.stringify(history));
    return true;
  } catch (error) {
    console.error("Failed to save recommendation history:", error);
    return false;
  }
}

/**
 * Load recommendation history from localStorage
 *
 * @returns {Array<{timestamp: string, timeString: string, recommendations: Array}>} Array of history entries
 */
export function loadRecommendationHistory() {
  try {
    const stored = localStorage.getItem(RECOMMENDATION_HISTORY_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error("Failed to load recommendation history:", error);
    return [];
  }
}

/**
 * Clear all recommendation history from localStorage
 *
 * @returns {boolean} True if clear was successful, false otherwise
 */
export function clearRecommendationHistory() {
  try {
    localStorage.removeItem(RECOMMENDATION_HISTORY_KEY);
    return true;
  } catch (error) {
    console.error("Failed to clear recommendation history:", error);
    return false;
  }
}
