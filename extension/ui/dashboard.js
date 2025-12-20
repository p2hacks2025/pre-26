import { fetchHistory } from "./historyProvider.js";
import { requestAnalysis, requestSuggestions } from "./apiClient.js";
import { renderGraph, updateNodeHighlight, addSuggestedNodesToGraph } from "./graphRenderer.js";
import { renderRecommendations, renderSuggestResults } from "./sidebar.js";
import {
  getCurrentData,
  setCurrentData,
  getSessionUuid,
  setSessionUuid,
  getSelectedNodes,
  setSelectedNodes,
  resetSelections,
  getSuggestedNodesData,
  resetSuggestedNodesData,
  appendSuggestedNodes
} from "./state.js";

const syncBtn = document.getElementById("sync-btn");
const rangeSelect = document.getElementById("range-select");
const statusEl = document.getElementById("status");
const graphEl = document.getElementById("graph");
const recommendList = document.getElementById("recommend-list");
const resetSelectionBtn = document.getElementById("reset-selection-btn");
const selectedNode1Label = document.getElementById("selected-node-1");
const selectedNode2Label = document.getElementById("selected-node-2");
const suggestStatus = document.getElementById("suggest-status");
const suggestList = document.getElementById("suggest-list");

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
  const selectedSuggestedNodes = getSuggestedNodesData();

  const trace = clickedPoint.data;
  if (trace.marker && trace.marker.symbol === "diamond" && trace.marker.color === "#00ff00") {
    const clickedSuggestedNode = selectedSuggestedNodes[nodeIndex];
    if (clickedSuggestedNode) {
      const searchQuery = clickedSuggestedNode.label;
      window.open(`https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`, "_blank");
      return;
    }
  }

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
  // 提案結果のみクリア（おすすめ検索ワードは残す）
  suggestStatus.textContent = "";
  suggestList.innerHTML = "";
}

async function handleSuggest() {
  const selectedNodes = getSelectedNodes();
  if (selectedNodes.length !== 2) {
    suggestStatus.textContent = "エラー: 2つのノードを選択してください";
    return;
  }

  const sessionUuid = getSessionUuid();
  if (!sessionUuid) {
    suggestStatus.textContent = "エラー: セッションUUIDがありません。先に「同期」を実行してください";
    return;
  }

  suggestStatus.textContent = "提案を取得中...";

  try {
    const suggestData = await requestSuggestions(
      sessionUuid,
      selectedNodes[0].id,
      selectedNodes[1].id
    );

    const currentData = getCurrentData();
    if (currentData) {
      addSuggestedNodesToGraph(
        currentData.nodes,
        suggestData.suggested_nodes,
        suggestData.suggested_edges
      );
      appendSuggestedNodes(suggestData.suggested_nodes);
    }

    renderSuggestResults(suggestList, suggestData);
    suggestStatus.textContent = `提案完了: ${suggestData.suggested_nodes.length}ノード追加`;
  } catch (error) {
    console.error("Suggest error:", error);
    suggestStatus.textContent = `エラー: ${error.message}`;
  }
}
