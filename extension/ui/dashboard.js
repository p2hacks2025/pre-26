const API_URL = "http://127.0.0.1:8080/api/analyze";
const MAX_HISTORY_ITEMS = 500;

let currentData = null;

// DOM要素
const syncBtn = document.getElementById("sync-btn");
const rangeSelect = document.getElementById("range-select");
const statusEl = document.getElementById("status");
const graphEl = document.getElementById("graph");
const recommendList = document.getElementById("recommend-list");
const nextList = document.getElementById("next-list");

// 初期化
document.addEventListener("DOMContentLoaded", () => {
  syncBtn.addEventListener("click", handleSync);
});

// 同期ボタンのハンドラ
async function handleSync() {
  syncBtn.disabled = true;
  statusEl.textContent = "履歴を取得中...";

  try {
    const history = await getHistory();
    statusEl.textContent = `${history.length}件の履歴を取得。解析中...`;

    const data = await analyzeHistory(history);
    currentData = data;
    renderGraph(data);
    renderSidebar(data);
    statusEl.textContent = `解析完了: ${data.nodes.length}ノード, ${data.edges.length}エッジ`;
  } catch (error) {
    console.error("Error:", error);
    statusEl.textContent = `エラー: ${error.message}`;

    // バックエンド不在時はモックデータを使用
    if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
      statusEl.textContent = "バックエンドに接続できません。モックデータを表示します。";
      await loadMockData();
    }
  } finally {
    syncBtn.disabled = false;
  }
}

// chrome.historyから履歴を取得
async function getHistory() {
  const hours = parseInt(rangeSelect.value);
  const endTime = Date.now();
  const startTime = endTime - hours * 60 * 60 * 1000;

  return new Promise((resolve, reject) => {
    if (!chrome?.history) {
      // 開発用: Chrome拡張外で実行時はダミーデータ
      resolve(generateDummyHistory());
      return;
    }

    chrome.history.search(
      {
        text: "",
        startTime: startTime,
        endTime: endTime,
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
          visitTime: item.lastVisitTime || Date.now(),
          visitCount: item.visitCount || 1
        }));

        resolve(history);
      }
    );
  });
}

// APIに履歴を送信して解析
async function analyzeHistory(history) {
  const hours = parseInt(rangeSelect.value);
  const currentTime = Date.now();
  const startTime = currentTime - hours * 60 * 60 * 1000;

  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      history: history,
      currentTime: currentTime,
      startTime: startTime,
      endTime: currentTime,
      maxNodes: 50
    })
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// モックデータを読み込み
async function loadMockData() {
  try {
    const response = await fetch("mock_response.json");
    const data = await response.json();
    currentData = data;
    renderGraph(data);
    renderSidebar(data);
    statusEl.textContent = "モックデータを表示中";
  } catch (error) {
    console.error("Mock data load error:", error);
    statusEl.textContent = "モックデータの読み込みに失敗しました";
  }
}

// Plotlyでネットワークグラフを描画
function renderGraph(data) {
  const { nodes, edges, path } = data;

  // ノードのトレース
  const nodeTrace = {
    x: nodes.map((n) => n.x),
    y: nodes.map((n) => n.y),
    mode: "markers+text",
    type: "scatter",
    text: nodes.map((n) => n.label),
    textposition: "top center",
    textfont: { color: "#fff", size: 10 },
    marker: {
      size: nodes.map((n) => Math.max(10, n.size)),
      color: nodes.map((_, i) => `hsl(${(i * 30) % 360}, 70%, 60%)`),
      line: { width: 2, color: "#fff" }
    },
    hoverinfo: "text",
    hovertext: nodes.map((n) => `${n.label}\n${n.hover_hints.join(", ")}`)
  };

  // エッジのトレース
  const edgeX = [];
  const edgeY = [];
  edges.forEach((edge) => {
    const source = nodes.find((n) => n.id === edge.source);
    const target = nodes.find((n) => n.id === edge.target);
    if (source && target) {
      edgeX.push(source.x, target.x, null);
      edgeY.push(source.y, target.y, null);
    }
  });

  const edgeTrace = {
    x: edgeX,
    y: edgeY,
    mode: "lines",
    type: "scatter",
    line: { width: 1, color: "rgba(255, 255, 255, 0.3)" },
    hoverinfo: "none"
  };

  // パスの軌跡（強調表示）
  const pathX = [];
  const pathY = [];
  const sortedPath = [...path].sort((a, b) => a.order - b.order);
  sortedPath.forEach((p) => {
    const node = nodes.find((n) => n.id === p.node_id);
    if (node) {
      pathX.push(node.x);
      pathY.push(node.y);
    }
  });

  const pathTrace = {
    x: pathX,
    y: pathY,
    mode: "lines",
    type: "scatter",
    line: { width: 3, color: "#ffcc00", dash: "dot" },
    hoverinfo: "none"
  };

  // next_nodesのトレース
  const nextNodes = data.next_nodes;
  const nextNodeTrace = {
    x: nextNodes.map((n) => n.x),
    y: nextNodes.map((n) => n.y),
    mode: "markers+text",
    type: "scatter",
    text: nextNodes.map((n) => n.label),
    textposition: "top center",
    textfont: { color: "#ffcc00", size: 10 },
    marker: {
      size: 15,
      color: "#ffcc00",
      symbol: "star",
      line: { width: 2, color: "#fff" }
    },
    hoverinfo: "text",
    hovertext: nextNodes.map((n) => `${n.label}\n${n.reason}`)
  };

  const layout = {
    showlegend: false,
    hovermode: "closest",
    xaxis: { showgrid: false, zeroline: false, showticklabels: false },
    yaxis: { showgrid: false, zeroline: false, showticklabels: false },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { l: 20, r: 20, t: 20, b: 20 }
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  Plotly.newPlot(graphEl, [edgeTrace, pathTrace, nodeTrace, nextNodeTrace], layout, config);
}

// サイドバーを描画
function renderSidebar(data) {
  // おすすめ検索ワード
  recommendList.innerHTML = "";
  data.recommend_queries.forEach((q) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="query-text">${q.query}</span>
      <span class="query-reason">${q.reason}</span>
    `;
    li.addEventListener("click", () => {
      window.open(`https://www.google.com/search?q=${encodeURIComponent(q.query)}`, "_blank");
    });
    recommendList.appendChild(li);
  });

  // 次に進むべき場所
  nextList.innerHTML = "";
  data.next_nodes.forEach((n) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="next-label">${n.label}</span>
      <span class="next-reason">${n.reason}</span>
    `;
    li.addEventListener("click", () => {
      window.open(n.url, "_blank");
    });
    nextList.appendChild(li);
  });
}

// 開発用ダミー履歴
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
    visitTime: Date.now() - i * 1000 * 60 * 30,
    visitCount: Math.floor(Math.random() * 10) + 1
  }));
}
