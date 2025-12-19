document.getElementById('openGraph').addEventListener('click', () => {
  // グラフの画面（フロントエンド）を新しいタブで開く
  chrome.tabs.create({ url: 'http://127.0.0.1:8000/' });
});