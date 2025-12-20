let graphElement = null;

export function renderGraph(element, data, onNodeClick) {
  graphElement = element;
  const { nodes, edges, path } = data;

  const nodeTrace = {
    x: nodes.map((n) => n.x),
    y: nodes.map((n) => n.y),
    mode: "markers+text",
    type: "scatter",
    text: nodes.map((n) => n.label),
    textposition: "top center",
    textfont: { color: "rgba(72,94,112,1)", size: 10 },
    marker: {
      size: nodes.map((n) => Math.max(10, n.size)),
      symbol: "star",
      line: { width: 2, color: "rgba(241, 207, 194, 1)" }
    },
    hoverinfo: "text",
    hovertext: nodes.map((n) => `${n.label}\n${n.hover_hints.join(", ")}`)
  };

  const { x: edgeX, y: edgeY } = buildEdgeCoordinates(nodes, edges);
  const edgeTrace = {
    x: edgeX,
    y: edgeY,
    mode: "lines",
    type: "scatter",
    line: { width: 1, color: "rgba(255, 255, 255, 0.3)" },
    hoverinfo: "none"
  };

  const { x: pathX, y: pathY } = buildPathCoordinates(nodes, path);
  const pathTrace = {
    x: pathX,
    y: pathY,
    mode: "lines",
    type: "scatter",
    line: { width: 3, color: "#C5B0CD", dash: "dot" },
    hoverinfo: "none"
  };

  const layout = {
    showlegend: false,
    hovermode: "closest",
    xaxis: { showgrid: false, zeroline: false, showticklabels: false, fixedrange: false},
    yaxis: { showgrid: false, zeroline: false, showticklabels: false, fixedrage: false },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { l: 20, r: 20, t: 20, b: 20 },
    dragmode: "pan",
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  Plotly.newPlot(graphElement, [edgeTrace, pathTrace, nodeTrace], layout, config);
  graphElement?.removeAllListeners?.("plotly_click");
  graphElement?.on?.("plotly_click", onNodeClick);
}

export function updateNodeHighlight(nodes, selectedNodes) {
  if (!graphElement || !nodes?.length) return;

  const sizes = nodes.map((n) => Math.max(10, n.size));
  // const colors = nodes.map((_, i) => `hsl(${(i * 30) % 360}, 70%, 60%)`);
  const colors = nodes.map((_, i) => "rgba(251, 184, 158, 1)");
  const lines = nodes.map((_, i) => "rgba(241, 207, 194, 1)");

  selectedNodes.forEach((selectedNode) => {
    const index = nodes.findIndex((n) => n.id === selectedNode.id);
    if (index !== -1) {
      sizes[index] = Math.max(10, nodes[index].size) * 0.8;
      colors[index] = "rgba(219, 105, 60, 1)";
      lines[index] = "rgba(219, 105, 60, 1)";
    }
  });

  Plotly.restyle(graphElement, {
    "marker.size": [sizes],
    "marker.color": [colors],
    "marker.line.color": [lines]
  }, [2]);
}

export function addSuggestedNodesToGraph(currentNodes, suggestedNodes, suggestedEdges) {
  if (!graphElement) return;

  const nodeTrace = {
    x: suggestedNodes.map((n) => n.x),
    y: suggestedNodes.map((n) => n.y),
    mode: "markers+text",
    type: "scatter",
    text: suggestedNodes.map((n) => n.label),
    textposition: "top center",
    textfont: { color: "#00ff00", size: 10 },
    marker: {
      size: suggestedNodes.map((n) => Math.max(10, n.size)),
      color: "#00ff00",
      symbol: "diamond",
      line: { width: 2, color: "#fff" }
    },
    hoverinfo: "text",
    hovertext: suggestedNodes.map((n) => `${n.label}\n理由: ${n.reason}\n${n.hover_hints.join(", ")}`)
  };

  const { x: newEdgeX, y: newEdgeY } = buildSuggestedEdgeCoordinates(currentNodes, suggestedNodes, suggestedEdges);
  const edgeTrace = {
    x: newEdgeX,
    y: newEdgeY,
    mode: "lines",
    type: "scatter",
    line: { width: 2, color: "#00ff00", dash: "dash" },
    hoverinfo: "none"
  };

  Plotly.addTraces(graphElement, [edgeTrace, nodeTrace]);
}

function buildEdgeCoordinates(nodes, edges) {
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
  return { x: edgeX, y: edgeY };
}

function buildPathCoordinates(nodes, path) {
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
  return { x: pathX, y: pathY };
}

function buildSuggestedEdgeCoordinates(existingNodes, suggestedNodes, suggestedEdges) {
  const edgeX = [];
  const edgeY = [];
  suggestedEdges.forEach((edge) => {
    const sourceNode = findNodeById(existingNodes, suggestedNodes, edge.source);
    const targetNode = findNodeById(existingNodes, suggestedNodes, edge.target);
    if (sourceNode && targetNode) {
      edgeX.push(sourceNode.x, targetNode.x, null);
      edgeY.push(sourceNode.y, targetNode.y, null);
    }
  });
  return { x: edgeX, y: edgeY };
}

function findNodeById(existingNodes, suggestedNodes, id) {
  return existingNodes.find((n) => n.id === id) ||
    suggestedNodes.find((n) => n.id === id);
}
