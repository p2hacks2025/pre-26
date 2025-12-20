import { API_ANALYZE_URL, API_SUGGEST_URL } from "./constants.js";

export async function requestAnalysis(history, hours) {
  const currentTime = Math.floor(Date.now());
  const startTime = Math.floor(currentTime - hours * 60 * 60 * 1000);

  const response = await fetch(API_ANALYZE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      history,
      currentTime,
      startTime,
      endTime: currentTime,
      maxNodes: 50
    })
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

export async function requestSuggestions(sessionUuid, nodeId1, nodeId2) {
  const response = await fetch(API_SUGGEST_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      uuid: sessionUuid,
      node_id_1: nodeId1,
      node_id_2: nodeId2
    })
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}
