// 検索エンジンのクエリパラメータ設定
const SEARCH_PARAMS = {
  'google.com': 'q',
  'yahoo.co.jp': 'p',
  'bing.com': 'q',
  'duckduckgo.com': 'q'
};

// APIサーバーのエンドポイント
const API_ENDPOINT = "http://127.0.0.1:8000/api/log";

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // 読み込みが完了(complete)し、かつURLが有効な場合のみ実行
  if (changeInfo.status === 'complete' && tab.url) {
    // chrome:// や edge:// などの内部ページは除外
    if (tab.url.startsWith('chrome:') || tab.url.startsWith('edge:') || tab.url.startsWith('about:')) {
      return;
    }

    try {
      const urlObj = new URL(tab.url);
      let searchWord = null;

      // ホスト名に基づいて検索ワードを抽出できるかチェック
      for (const [domain, param] of Object.entries(SEARCH_PARAMS)) {
        if (urlObj.hostname.includes(domain)) {
          const word = urlObj.searchParams.get(param);
          if (word) {
            searchWord = word;
            break; 
          }
        }
      }

      // 送信するデータオブジェクト
      const logData = {
        timestamp: new Date().toISOString(),
        title: tab.title,
        url: tab.url,
        searchWord: searchWord,
        domain: urlObj.hostname
      };

      console.log("Processing:", tab.title);

      // バックエンドへ送信
      sendToBackend(logData);

    } catch (e) {
      console.error("URL解析エラー:", e);
    }
  }
});

function sendToBackend(data) {
  fetch(API_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  })
  .then(res => {
    if (!res.ok) throw new Error(`HTTP Status ${res.status}`);
    return res.json();
  })
  .then(json => console.log("Sent to backend successfully:", json))
  .catch(err => {
    // サーバーが起動していない場合ここに来る
    console.log("Backend connect error (Server might be offline):", err);
  });
}