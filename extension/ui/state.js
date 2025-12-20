import { SESSION_UUID_KEY } from "./constants.js";

const state = {
  currentData: null,
  sessionUuid: null,
  selectedNodes: [],
  suggestedNodesData: []
};

const storedUuid = typeof localStorage !== "undefined"
  ? localStorage.getItem(SESSION_UUID_KEY)
  : null;

if (storedUuid) {
  state.sessionUuid = storedUuid;
}

export function getCurrentData() {
  return state.currentData;
}

export function setCurrentData(data) {
  state.currentData = data;
}

export function getSessionUuid() {
  return state.sessionUuid;
}

export function setSessionUuid(uuid) {
  state.sessionUuid = uuid;
  if (typeof localStorage !== "undefined" && uuid) {
    localStorage.setItem(SESSION_UUID_KEY, uuid);
  }
}

export function clearSessionUuid() {
  state.sessionUuid = null;
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem(SESSION_UUID_KEY);
  }
}

export function getSelectedNodes() {
  return state.selectedNodes;
}

export function setSelectedNodes(nodes) {
  state.selectedNodes = nodes;
}

export function getSuggestedNodesData() {
  return state.suggestedNodesData;
}

export function resetSuggestedNodesData() {
  state.suggestedNodesData = [];
}

export function appendSuggestedNodes(nodes) {
  state.suggestedNodesData = [
    ...state.suggestedNodesData,
    ...nodes
  ];
}

export function resetSelections() {
  state.selectedNodes = [];
}
