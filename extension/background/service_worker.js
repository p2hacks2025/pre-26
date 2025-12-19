// Actionクリックでダッシュボードを新規タブで開く
chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({
    url: chrome.runtime.getURL("ui/dashboard.html")
  });
});
