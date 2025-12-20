/**
 * Sidebar Module
 *
 * Re-exports recommendation rendering functionality.
 * This module now delegates to the centralized recommendationRenderer module.
 */

import { renderRecommendationList } from "./recommendationRenderer.js";

/**
 * Render recommendations into a list element
 *
 * @param {HTMLElement} listElement - The UL element to render into
 * @param {Array<{query: string, reason: string}>} recommendQueries - Array of recommendations
 */
export function renderRecommendations(listElement, recommendQueries) {
  renderRecommendationList(listElement, recommendQueries, {
    clearExisting: true,
    enableClick: true
  });
}
