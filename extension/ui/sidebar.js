export function renderRecommendations(listElement, recommendQueries) {
  listElement.innerHTML = "";
  recommendQueries.forEach((q) => {
    const li = document.createElement("li");
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

export function renderSuggestResults(listElement, suggestData) {
  listElement.innerHTML = "";

  suggestData.search_queries.forEach((query) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="suggest-query">${query}</span>`;
    li.addEventListener("click", () => {
      window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, "_blank");
    });
    listElement.appendChild(li);
  });

  suggestData.suggested_nodes.forEach((node) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="suggest-label">${node.label}</span>
      <span class="suggest-reason">${node.reason}</span>
    `;
    li.addEventListener("click", () => {
      window.open(node.url, "_blank");
    });
    listElement.appendChild(li);
  });
}
