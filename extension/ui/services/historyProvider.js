import { MAX_HISTORY_ITEMS } from "../core/constants.js";

export async function fetchHistory(hours) {
  const endTime = Date.now();
  const startTime = endTime - hours * 60 * 60 * 1000;

  return new Promise((resolve, reject) => {
    if (!chrome?.history) {
      resolve(generateDummyHistory());
      return;
    }

    chrome.history.search(
      {
        text: "",
        startTime,
        endTime,
        maxResults: MAX_HISTORY_ITEMS
      },
      (results) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }

        const history = results.map((item) => ({
          url: item.url,
          title: item.title || "",
          visitTime: Math.floor(item.lastVisitTime || Date.now()),
          visitCount: item.visitCount || 1
        }));

        resolve(history);
      }
    );
  });
}

function generateDummyHistory() {
  const sites = [
    { url: "https://github.com", title: "GitHub" },
    { url: "https://stackoverflow.com", title: "Stack Overflow" },
    { url: "https://google.com", title: "Google" },
    { url: "https://youtube.com", title: "YouTube" },
    { url: "https://twitter.com", title: "Twitter" }
  ];

  return sites.map((site, i) => ({
    url: site.url,
    title: site.title,
    visitTime: Math.floor(Date.now() - i * 1000 * 60 * 30),
    visitCount: Math.floor(Math.random() * 10) + 1
  }));
}
