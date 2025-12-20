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

document.addEventListener("DOMContentLoaded", () => {
  syncBtn.addEventListener("click", handleSync);
  resetSelectionBtn.addEventListener("click", resetNodeSelection);

  const savedUuid = getSessionUuid();
  if (savedUuid) {
    console.log("Session UUID restored:", savedUuid);
  }
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
      // タイムスタンプセパレーターを追加
      const separator = document.createElement("div");
      separator.className = "recommendation-separator";
      const now = new Date();
      const timeString = now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
      separator.textContent = `${timeString} の推薦`;

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
