// 検索エンジンのクエリパラメータ設定
// Googleは'q', Yahooは'p', Bingは'q'などが一般的です
const SEARCH_PARAMS = {
  'google.com': 'q',
  'yahoo.co.jp': 'p',
  'bing.com': 'q',
  'duckduckgo.com': 'q'
};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // 読み込みが完了(complete)し、かつURLが有効な場合のみ実行
  if (changeInfo.status === 'complete' && tab.url) {
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

      // 保存するデータオブジェクト
      const logData = {
        timestamp: new Date().toISOString(), // 検索時間
        title: tab.title,                    // ページタイトル
        url: tab.url,                        // URL
        searchWord: searchWord,              // 検索ワード (なければnull)
        domain: urlObj.hostname
      };

      // ストレージに追加保存
      saveToStorage(logData);

    } catch (e) {
      console.error("URL解析エラー:", e);
    }
  }
});

function saveToStorage(newItem) {
  chrome.storage.local.get(['historyLogs'], (result) => {
    const logs = result.historyLogs || [];
    logs.push(newItem);
    
    // データが多すぎる場合の安全策（任意：最新1000件保持など）
    // if (logs.length > 1000) logs.shift(); 

    chrome.storage.local.set({ historyLogs: logs }, () => {
      console.log('Log saved:', newItem.title);
    });
  });
}