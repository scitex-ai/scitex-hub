/**
 * Hub Explore — tab switching and user profile links in the Explore view.
 */

import { loadExplore, loadUserProfile } from "./hub-navigate";

/**
 * Handle clicks originating from the Explore content area.
 * Returns true if the event was handled.
 */
export function handleExploreClick(target: HTMLElement, e: Event): boolean {
  // Explore tab clicks (Repositories / Users / Organizations)
  const exploreTab = target.closest(
    "a.hub-explore-tab[data-explore-tab]",
  ) as HTMLAnchorElement | null;
  if (exploreTab) {
    e.preventDefault();
    loadExplore(exploreTab.getAttribute("data-explore-tab") || "repositories");
    return true;
  }

  // Explore user profile links
  const userLink = target.closest(
    "a.hub-explore-user",
  ) as HTMLAnchorElement | null;
  if (userLink) {
    e.preventDefault();
    loadUserProfile(userLink.getAttribute("data-username") || "");
    return true;
  }

  return false;
}
