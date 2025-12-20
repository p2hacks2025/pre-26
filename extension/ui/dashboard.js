import { fetchHistory } from "./historyProvider.js";
import { requestAnalysis, requestSuggestions } from "./apiClient.js";
import { renderGraph, updateNodeHighlight } from "./graphRenderer.js";
import { renderRecommendations } from "./sidebar.js";
import {
  getCurrentData,
  setCurrentData,
  getSessionUuid,
  setSessionUuid,
  getSelectedNodes,
  setSelectedNodes,
  resetSelections,
  resetSuggestedNodesData
} from "./state.js";

const syncBtn = document.getElementById("sync-btn");
const rangeSelect = document.getElementById("range-select");
const statusEl = document.getElementById("status");
const graphEl = document.getElementById("graph");
const recommendList = document.getElementById("recommend-list");
const previousRecommendList = document.getElementById("previous-recommend-list");
const previousRecommendSection = document.getElementById("previous-recommend-section");
const resetSelectionBtn = document.getElementById("reset-selection-btn");
const selectedNode1Label = document.getElementById("selected-node-1");
const selectedNode2Label = document.getElementById("selected-node-2");

// localStorage関連の定数とユーティリティ関数
const RECOMMENDATION_HISTORY_KEY = "sparknavi_recommendation_history";

/**
 * 推薦履歴をlocalStorageに保存
 * @param {Array} recommendations - { query, reason } の配列
 * @param {string} timeString - 時刻文字列（例: "14:30"）
 */
function saveRecommendationToHistory(recommendations, timeString) {
  try {
    const history = loadRecommendationHistory();
    const newEntry = {
      timestamp: new Date().toISOString(),
      timeString: timeString,
      recommendations: recommendations
    };

    // 新しいエントリを先頭に追加
    history.unshift(newEntry);

    // 最大50件まで保存（古いものから削除）
    if (history.length > 50) {
      history.splice(50);
    }

    localStorage.setItem(RECOMMENDATION_HISTORY_KEY, JSON.stringify(history));
  } catch (error) {
    console.error("Failed to save recommendation history:", error);
  }
}

/**
 * localStorageから推薦履歴を読み込み
 * @returns {Array} 推薦履歴の配列
 */
function loadRecommendationHistory() {
  try {
    const stored = localStorage.getItem(RECOMMENDATION_HISTORY_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error("Failed to load recommendation history:", error);
    return [];
  }
}

/**
 * 推薦履歴をlocalStorageから削除
 */
function clearRecommendationHistory() {
  try {
    localStorage.removeItem(RECOMMENDATION_HISTORY_KEY);
  } catch (error) {
    console.error("Failed to clear recommendation history:", error);
  }
}

/**
 * 推薦履歴をDOMに復元
 */
function restoreRecommendationHistory() {
  const history = loadRecommendationHistory();

  if (history.length === 0) {
    return;
  }

  // 履歴を古い順にDOMに追加（最終的に新しいものが上に来る）
  history.reverse().forEach(entry => {
    // タイムスタンプセパレーターを作成
    const separator = document.createElement("div");
    separator.className = "recommendation-separator";
    separator.textContent = `${entry.timeString} の推薦`;
    previousRecommendList.appendChild(separator);

    // 推薦アイテムを作成
    entry.recommendations.forEach(rec => {
      const li = document.createElement("li");
      const isAISuggestion = rec.reason && rec.reason.includes("🤖");
      if (isAISuggestion) {
        li.classList.add("ai-suggestion");
      }
      li.innerHTML = `
        <span class="query-text">${rec.query}</span>
        <span class="query-reason">${rec.reason}</span>
      `;
      li.addEventListener("click", () => {
        window.open(`https://www.google.com/search?q=${encodeURIComponent(rec.query)}`, "_blank");
      });
      previousRecommendList.appendChild(li);
    });
  });

  // セクションを表示
  if (history.length > 0) {
    previousRecommendSection.style.display = "block";
  }
}

/**
 * リスト要素から推薦データを抽出
 * @param {HTMLElement} listElement - UL要素
 * @returns {Array} { query, reason } の配列
 */
function extractRecommendationsFromList(listElement) {
  const recommendations = [];
  Array.from(listElement.children).forEach(child => {
    const queryText = child.querySelector('.query-text')?.textContent;
    const queryReason = child.querySelector('.query-reason')?.textContent;
    if (queryText && queryReason) {
      recommendations.push({ query: queryText, reason: queryReason });
    }
  });
  return recommendations;
}

document.addEventListener("DOMContentLoaded", () => {
  syncBtn.addEventListener("click", handleSync);
  resetSelectionBtn.addEventListener("click", resetNodeSelection);

  const savedUuid = getSessionUuid();
  if (savedUuid) {
    console.log("Session UUID restored:", savedUuid);
  }

  // 保存されている推薦履歴を復元
  restoreRecommendationHistory();
  console.log("Recommendation history restored from localStorage");
});

async function handleSync() {
  syncBtn.disabled = true;
  statusEl.textContent = "履歴を取得中...";
  resetSelections();
  resetSuggestedNodesData();

  try {
    const hours = parseInt(rangeSelect.value);
    const history = await fetchHistory(hours);
    statusEl.textContent = `${history.length}件の履歴を取得。解析中...`;

    const data = await requestAnalysis(history, hours);
    setCurrentData(data);

    if (data.uuid) {
      setSessionUuid(data.uuid);
      console.log("Session UUID saved:", data.uuid);
    }

    renderGraph(graphEl, data, handleNodeClick);
    renderRecommendations(recommendList, data.recommend_queries);
    updateSelectionUI();
    updateNodeHighlight(data.nodes, getSelectedNodes());
    statusEl.textContent = `解析完了: ${data.nodes.length}ノード, ${data.edges.length}エッジ`;
  } catch (error) {
    console.error("Error:", error);
    statusEl.textContent = `エラー: ${error.message}`;

    if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
      statusEl.textContent = "バックエンドに接続できません。モックデータを表示します。";
      await loadMockData();
    }
  } finally {
    syncBtn.disabled = false;
  }
}

async function loadMockData() {
  try {
    const response = await fetch("mock_response.json");
    const data = await response.json();
    setCurrentData(data);
    renderGraph(graphEl, data, handleNodeClick);
    renderRecommendations(recommendList, data.recommend_queries);
    updateNodeHighlight(data.nodes, getSelectedNodes());
    statusEl.textContent = "モックデータを表示中";
  } catch (error) {
    console.error("Mock data load error:", error);
    statusEl.textContent = "モックデータの読み込みに失敗しました";
  }
}

function handleNodeClick(event) {
  const clickedPoint = event.points[0];
  const nodeIndex = clickedPoint.pointIndex;

  if (clickedPoint.curveNumber !== 2) {
    return;
  }

  const dataSet = getCurrentData();
  if (!dataSet) return;

  const clickedNode = dataSet.nodes[nodeIndex];
  if (!clickedNode) return;

  const selectedNodes = getSelectedNodes();
  const existingIndex = selectedNodes.findIndex((n) => n.id === clickedNode.id);
  if (existingIndex !== -1) {
    selectedNodes.splice(existingIndex, 1);
    updateSelectionUI();
    updateNodeHighlight(dataSet.nodes, selectedNodes);
    return;
  }

  if (selectedNodes.length >= 2) {
    setSelectedNodes([clickedNode]);
  } else {
    selectedNodes.push(clickedNode);
  }

  updateSelectionUI();
  updateNodeHighlight(dataSet.nodes, selectedNodes);

  if (selectedNodes.length === 2) {
    handleSuggest();
  }
}

function updateSelectionUI() {
  const selectedNodes = getSelectedNodes();
  if (selectedNodes.length >= 1) {
    selectedNode1Label.textContent = selectedNodes[0].label;
    selectedNode1Label.className = "selected-node-label active";
  } else {
    selectedNode1Label.textContent = "未選択";
    selectedNode1Label.className = "selected-node-label";
  }

  if (selectedNodes.length >= 2) {
    selectedNode2Label.textContent = selectedNodes[1].label;
    selectedNode2Label.className = "selected-node-label active";
  } else {
    selectedNode2Label.textContent = "未選択";
    selectedNode2Label.className = "selected-node-label";
  }
}

function resetNodeSelection() {
  resetSelections();
  updateSelectionUI();
  const dataSet = getCurrentData();
  if (dataSet) {
    updateNodeHighlight(dataSet.nodes, getSelectedNodes());
  }
  // 以前のおすすめセクションをクリアして非表示に
  previousRecommendList.innerHTML = "";
  previousRecommendSection.style.display = "none";

  // localStorageから推薦履歴を削除
  clearRecommendationHistory();
  console.log("Recommendation history cleared from localStorage");
}

async function handleSuggest() {
  const selectedNodes = getSelectedNodes();
  if (selectedNodes.length !== 2) {
    statusEl.textContent = "エラー: 2つのノードを選択してください";
    return;
  }

  const sessionUuid = getSessionUuid();
  if (!sessionUuid) {
    statusEl.textContent = "エラー: セッションUUIDがありません。先に「同期」を実行してください";
    return;
  }

  statusEl.textContent = "提案を取得中...";

  try {
    const suggestData = await requestSuggestions(
      sessionUuid,
      selectedNodes[0].id,
      selectedNodes[1].id
    );

    // 既存のおすすめを「以前のおすすめ」に追加（上書きではなく追加）
    if (recommendList.children.length > 0) {
      // 現在の推薦をデータとして抽出
      const currentRecommendations = extractRecommendationsFromList(recommendList);

      // タイムスタンプセパレーターを追加
      const separator = document.createElement("div");
      separator.className = "recommendation-separator";
      const now = new Date();
      const timeString = now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
      separator.textContent = `${timeString} の推薦`;

      // localStorageに保存
      saveRecommendationToHistory(currentRecommendations, timeString);

      // 既存の内容の前に挿入（新しいものが上に来るように）
      previousRecommendList.insertBefore(separator, previousRecommendList.firstChild);

      // 現在のおすすめを1つずつ追加
      Array.from(recommendList.children).reverse().forEach(child => {
        const clonedChild = child.cloneNode(true);
        previousRecommendList.insertBefore(clonedChild, previousRecommendList.firstChild);
      });

      previousRecommendSection.style.display = "block";
    }

    // 提案キーワードを「おすすめ検索ワード」形式に変換
    const suggestedQueries = suggestData.search_queries.map(query => ({
      query: query,
      reason: "🤖 AI提案"
    }));

    renderRecommendations(recommendList, suggestedQueries);
    statusEl.textContent = `AI提案: ${suggestData.search_queries.length}個の検索キーワード`;
  } catch (error) {
    console.error("Suggest error:", error);
    statusEl.textContent = `エラー: ${error.message}`;
  }
}
