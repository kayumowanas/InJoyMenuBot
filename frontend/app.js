const statusNode = document.getElementById("status");
const gridNode = document.getElementById("menu-grid");
const selectNode = document.getElementById("category-select");
const refreshBtn = document.getElementById("refresh-btn");
const template = document.getElementById("item-card-template");

let allItems = [];

function formatPrice(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  if (Number.isInteger(numeric)) {
    return `${numeric} RUB`;
  }
  return `${numeric.toFixed(2)} RUB`;
}

function normalizeText(value) {
  return String(value || "").trim();
}

function renderItems(items) {
  gridNode.innerHTML = "";
  if (items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No items in this category right now.";
    gridNode.appendChild(empty);
    return;
  }

  for (const item of items) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".item-name").textContent = normalizeText(item.name) || "Untitled";
    node.querySelector(".item-description").textContent = normalizeText(item.description) || "No description";
    node.querySelector(".item-price").textContent = formatPrice(item.price);
    gridNode.appendChild(node);
  }
}

function rebuildCategoryOptions(items) {
  const current = selectNode.value;
  const categories = [...new Set(items.map((item) => normalizeText(item.category) || "Other"))]
    .sort((a, b) => a.localeCompare(b));

  selectNode.innerHTML = "";

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "All categories";
  selectNode.appendChild(allOption);

  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    selectNode.appendChild(option);
  }

  selectNode.value = categories.includes(current) ? current : "";
}

function applyFilter() {
  const selectedCategory = normalizeText(selectNode.value);
  const filtered = selectedCategory
    ? allItems.filter((item) => normalizeText(item.category) === selectedCategory)
    : allItems;

  renderItems(filtered);
  statusNode.textContent = `Items shown: ${filtered.length} of ${allItems.length}`;
}

async function loadMenu() {
  statusNode.textContent = "Loading menu...";
  refreshBtn.disabled = true;
  try {
    const response = await fetch("/api/public/menu");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    allItems = Array.isArray(payload) ? payload : [];
    rebuildCategoryOptions(allItems);
    applyFilter();
  } catch (error) {
    gridNode.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Failed to load menu. Check that backend is running.";
    gridNode.appendChild(empty);
    statusNode.textContent = `Request failed: ${error instanceof Error ? error.message : "unknown error"}`;
  } finally {
    refreshBtn.disabled = false;
  }
}

selectNode.addEventListener("change", applyFilter);
refreshBtn.addEventListener("click", loadMenu);

loadMenu();
