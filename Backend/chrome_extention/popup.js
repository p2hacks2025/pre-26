// 状態表示の更新
function updateDisplay() {
  chrome.storage.local.get(['historyLogs'], (result) => {
    const logs = result.historyLogs || [];
    document.getElementById('countDisplay').textContent = `記録数: ${logs.length}件`;
  });
}

// 初期表示
updateDisplay();

// エクスポート処理
document.getElementById('exportBtn').addEventListener('click', () => {
  chrome.storage.local.get(['historyLogs'], (result) => {
    const logs = result.historyLogs || [];
    if (logs.length === 0) {
      alert("ログがありません");
      return;
    }

    const jsonString = JSON.stringify(logs, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // 現在日時を取得してファイル名にする
    // 例: search_log_20251216_183000.json
    const now = new Date();
    const timestamp = now.getFullYear() +
                      ('0' + (now.getMonth() + 1)).slice(-2) +
                      ('0' + now.getDate()).slice(-2) + '_' +
                      ('0' + now.getHours()).slice(-2) +
                      ('0' + now.getMinutes()).slice(-2) +
                      ('0' + now.getSeconds()).slice(-2);

    const filename = `search_log_${timestamp}.json`;

    // ダウンロード実行
    chrome.downloads.download({
      url: url,
      filename: filename,
      saveAs: false // ダイアログを出さずに即保存（設定による）
    }, (downloadId) => {
      document.getElementById('status').textContent = "保存完了: " + filename;
    });
  });
});

// ログ消去処理
document.getElementById('clearBtn').addEventListener('click', () => {
  if(confirm("ログを全て消去しますか？")) {
    chrome.storage.local.set({ historyLogs: [] }, () => {
      updateDisplay();
      document.getElementById('status').textContent = "ログを消去しました";
    });
  }
});