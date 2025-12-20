export function renderRecommendations(listElement, recommendQueries) {
  listElement.innerHTML = "";
  recommendQueries.forEach((q) => {
    const li = document.createElement("li");
    // AI提案の場合は特別なクラスを追加
    const isAISuggestion = q.reason && q.reason.includes("🤖");
    if (isAISuggestion) {
      li.classList.add("ai-suggestion");
    }
    li.innerHTML = `
      <span class="query-text">${q.query}</span>
      <span class="query-reason">${q.reason}</span>
    `;
    li.addEventListener("click", () => {
      window.open(`https://www.google.com/search?q=${encodeURIComponent(q.query)}`, "_blank");
    });
    listElement.appendChild(li);
  });
}
