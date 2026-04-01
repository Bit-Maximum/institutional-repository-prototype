document.addEventListener("DOMContentLoaded", () => {
  const selects = Array.from(document.querySelectorAll("select[data-enhance-search-select='true']"));

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

  const components = new Map();
  const allInstances = [];

  const advancedPanel = document.querySelector("[data-search-advanced-panel]");
  const advancedToggle = document.querySelector("[data-search-advanced-toggle]");
  const advancedToggleLabel = document.querySelector("[data-search-advanced-toggle-label]");
  const advancedBody = document.querySelector("[data-search-advanced-body]");
  const showFiltersLabel = "Показать фильтры";
  const hideFiltersLabel = "Скрыть фильтры";

  const setAdvancedOpen = (open) => {
    if (!advancedPanel || !advancedToggle || !advancedBody || !advancedToggleLabel) return;
    advancedPanel.classList.toggle("is-open", open);
    if (open) {
      animateShow(advancedBody, 'is-open');
    } else {
      animateHide(advancedBody, 'is-open', 'is-closing');
      closeAll();
    }
    advancedToggle.setAttribute("aria-expanded", open ? "true" : "false");
    advancedToggleLabel.textContent = open ? hideFiltersLabel : showFiltersLabel;
  };

  const closeAll = (except = null) => {
    allInstances.forEach((instance) => {
      if (instance !== except) {
        instance.close();
      }
    });
  };

  const animateHide = (element, className, hiddenClassName = className) => {
    if (!element || element.hidden) return;
    element.classList.remove(className);
    element.classList.add(hiddenClassName);
    window.setTimeout(() => {
      if (!element.classList.contains(className)) {
        element.hidden = true;
        element.classList.remove(hiddenClassName);
      }
    }, 180);
  };

  const animateShow = (element, className) => {
    if (!element) return;
    element.hidden = false;
    element.classList.remove('is-closing');
    window.requestAnimationFrame(() => {
      element.classList.add(className);
    });
  };

  const setImmediateState = (element, open, className = 'is-open') => {
    if (!element) return;
    element.hidden = !open;
    element.classList.toggle(className, open);
    element.classList.remove('is-closing');
  };

  const searchShell = document.querySelector('[data-search-shell]');
  const searchShellSummary = document.querySelector('[data-search-shell-summary]');
  const searchShellForm = document.querySelector('[data-search-shell-form]');
  const searchShellExpand = document.querySelector('[data-search-shell-expand]');
  const searchShellCollapse = document.querySelector('[data-search-shell-collapse]');

  const setSearchShellCollapsed = (collapsed, immediate = false) => {
    if (!searchShell || !searchShellSummary || !searchShellForm) return;
    searchShell.classList.toggle('is-collapsed', collapsed);
    const show = immediate ? setImmediateState : animateShow;
    const hide = immediate ? ((el) => setImmediateState(el, false)) : ((el) => animateHide(el, 'is-open', 'is-closing'));
    if (collapsed) {
      show(searchShellSummary, 'is-open');
      hide(searchShellForm);
      closeAll();
    } else {
      hide(searchShellSummary);
      show(searchShellForm, 'is-open');
    }
  };

  if (searchShell && searchShellSummary && searchShellForm) {
    const shouldStartCollapsed = searchShell.dataset.initialCollapsed === 'true';
    setSearchShellCollapsed(shouldStartCollapsed, true);
    searchShellExpand?.addEventListener('click', () => setSearchShellCollapsed(false));
    searchShellCollapse?.addEventListener('click', () => setSearchShellCollapsed(true));
  }

  document.querySelectorAll('.search-explanation').forEach((details) => {
    const summary = details.querySelector('summary');
    const body = details.querySelector('.search-explanation__body');
    if (!summary || !body) return;

    setImmediateState(body, details.hasAttribute('open'));
    summary.setAttribute('aria-expanded', details.hasAttribute('open') ? 'true' : 'false');

    summary.addEventListener('click', (event) => {
      event.preventDefault();
      const willOpen = !details.open;
      if (willOpen) {
        details.open = true;
        summary.setAttribute('aria-expanded', 'true');
        animateShow(body, 'is-open');
      } else {
        summary.setAttribute('aria-expanded', 'false');
        animateHide(body, 'is-open', 'is-closing');
        window.setTimeout(() => {
          if (body.hidden) {
            details.open = false;
          }
        }, 190);
      }
    });
  });

  const createComponent = (select) => {
    select.classList.add("search-select-native");
    const wrapper = document.createElement("div");
    wrapper.className = "filter-picker";
    wrapper.innerHTML = `
      <button type="button" class="filter-picker__trigger" aria-expanded="false">
        <span class="filter-picker__trigger-text"></span>
        <span class="filter-picker__trigger-count" hidden></span>
      </button>
      <div class="filter-picker__selection" hidden></div>
      <div class="filter-picker__dropdown" hidden>
        <div class="filter-picker__search-shell">
          <input type="search" class="filter-picker__search" autocomplete="off">
        </div>
        <div class="filter-picker__options"></div>
      </div>
    `;
    select.insertAdjacentElement("afterend", wrapper);

    const trigger = wrapper.querySelector(".filter-picker__trigger");
    const triggerText = wrapper.querySelector(".filter-picker__trigger-text");
    const triggerCount = wrapper.querySelector(".filter-picker__trigger-count");
    const selection = wrapper.querySelector(".filter-picker__selection");
    const dropdown = wrapper.querySelector(".filter-picker__dropdown");
    const search = wrapper.querySelector(".filter-picker__search");
    const optionsHost = wrapper.querySelector(".filter-picker__options");

    const placeholder = select.dataset.placeholder || trigger.closest(".search-filter-field")?.querySelector("label")?.textContent?.trim() || "";
    const noResultsLabel = select.dataset.noResultsLabel || "";
    const selectedManyLabel = select.dataset.selectedManyLabel || "";
    const isMultiple = select.multiple;
    const enableSearch = select.dataset.enableSearch !== "false";
    search.placeholder = `${placeholder}…`;
    if (!enableSearch) {
      search.hidden = true;
      search.tabIndex = -1;
      wrapper.classList.add("filter-picker--no-search");
    }

    const instance = {
      select,
      wrapper,
      trigger,
      dropdown,
      search,
      optionsHost,
      selection,
      get options() {
        return Array.from(select.options);
      },
      open() {
        closeAll(instance);
        wrapper.classList.add("is-open");
        wrapper.closest('.search-filter-field, .stack-xs')?.classList.add('is-filter-open');
        trigger.setAttribute("aria-expanded", "true");
        animateShow(dropdown, 'is-open');
        if (enableSearch) {
          window.requestAnimationFrame(() => search.focus());
        }
      },
      close() {
        wrapper.classList.remove("is-open");
        wrapper.closest('.search-filter-field, .stack-xs')?.classList.remove('is-filter-open');
        trigger.setAttribute("aria-expanded", "false");
        animateHide(dropdown, 'is-open', 'is-closing');
        search.value = "";
        renderOptions();
      },
      toggle() {
        if (wrapper.classList.contains("is-open")) {
          instance.close();
        } else {
          instance.open();
        }
      },
      refresh() {
        renderSelection();
        renderOptions();
      },
      getSelectedValues() {
        return instance.options.filter((option) => option.selected).map((option) => String(option.value));
      },
      isMultiple,
    };

    const selectedSummary = () => {
      const selected = instance.options.filter((option) => option.selected);
      if (!selected.length) {
        triggerText.textContent = placeholder;
        triggerCount.hidden = true;
        triggerCount.textContent = "";
        return;
      }
      if (isMultiple) {
        triggerText.textContent = selectedManyLabel || placeholder;
        triggerCount.hidden = false;
        triggerCount.textContent = String(selected.length);
        return;
      }
      triggerText.textContent = selected[0].textContent.trim();
      triggerCount.hidden = true;
      triggerCount.textContent = "";
    };

    const renderSelection = () => {
      const selected = instance.options.filter((option) => option.selected);
      selectedSummary();
      if (!selected.length || !isMultiple) {
        selection.hidden = true;
        selection.innerHTML = "";
        return;
      }
      selection.hidden = false;
      selection.innerHTML = selected.map((option) => `
        <button type="button" class="filter-chip" data-filter-chip-value="${escapeHtml(option.value)}">
          <span>${escapeHtml(option.textContent.trim())}</span>
          <span aria-hidden="true">×</span>
        </button>
      `).join("");
    };

    const isVisibleOption = (option) => {
      const allowedTypes = select.dataset.allowedTypeIds ? select.dataset.allowedTypeIds.split(",").filter(Boolean) : [];
      if (!allowedTypes.length) return true;
      const optionType = option.dataset.publicationType;
      return !optionType || allowedTypes.includes(optionType);
    };

    const renderOptions = () => {
      const query = search.value.trim().toLowerCase();
      const visibleOptions = instance.options.filter((option) => {
        if (!isVisibleOption(option)) return false;
        if (!query) return true;
        return option.textContent.toLowerCase().includes(query);
      });
      if (!visibleOptions.length) {
        optionsHost.innerHTML = `<div class="filter-picker__empty">${escapeHtml(noResultsLabel)}</div>`;
        return;
      }
      optionsHost.innerHTML = visibleOptions.map((option) => `
        <button type="button" class="filter-picker__option${option.selected ? " is-selected" : ""}" data-filter-option-value="${escapeHtml(option.value)}">
          <span class="filter-picker__option-label">${escapeHtml(option.textContent.trim())}</span>
          ${option.selected ? '<span class="filter-picker__option-mark" aria-hidden="true">✓</span>' : ""}
        </button>
      `).join("");
    };

    const setSelected = (value, selected) => {
      const option = instance.options.find((item) => String(item.value) === String(value));
      if (!option) return;
      option.selected = selected;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      instance.refresh();
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      instance.toggle();
    });

    if (enableSearch) {
      search.addEventListener("input", () => renderOptions());
    }

    optionsHost.addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter-option-value]");
      if (!button) return;
      const value = button.dataset.filterOptionValue;
      const option = instance.options.find((item) => String(item.value) === String(value));
      if (!option) return;
      if (isMultiple) {
        setSelected(value, !option.selected);
      } else {
        instance.options.forEach((item) => {
          item.selected = String(item.value) === String(value);
        });
        select.dispatchEvent(new Event("change", { bubbles: true }));
        instance.refresh();
        instance.close();
      }
    });

    selection.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-filter-chip-value]");
      if (!chip || !isMultiple) return;
      setSelected(chip.dataset.filterChipValue, false);
    });

    select.addEventListener("change", () => instance.refresh());

    instance.refresh();
    components.set(select.name, instance);
    allInstances.push(instance);
    return instance;
  };

  if (selects.length) {
    selects.forEach(createComponent);
  }

  const syncSubtypeVisibility = () => {
    const typeInstance = components.get("publication_type");
    const subtypeInstance = components.get("publication_subtype");
    if (!typeInstance || !subtypeInstance) return;

    const selectedTypeIds = typeInstance.getSelectedValues();
    subtypeInstance.select.dataset.allowedTypeIds = selectedTypeIds.join(",");

    subtypeInstance.options.forEach((option) => {
      const optionType = option.dataset.publicationType;
      const isAllowed = !selectedTypeIds.length || !optionType || selectedTypeIds.includes(optionType);
      if (!isAllowed) {
        option.selected = false;
      }
    });

    subtypeInstance.select.dispatchEvent(new Event("change", { bubbles: true }));
    subtypeInstance.refresh();
  };

  const typeSelect = document.querySelector("select[name='publication_type']");
  if (typeSelect && selects.length) {
    typeSelect.addEventListener("change", syncSubtypeVisibility);
    syncSubtypeVisibility();
  }

  document.addEventListener("click", (event) => {
    const insidePicker = event.target.closest(".filter-picker");
    if (!insidePicker) {
      closeAll();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAll();
    }
  });

  if (advancedPanel && advancedToggle && advancedBody) {
    const shouldStartOpen = advancedPanel.dataset.initialOpen === "true";
    setAdvancedOpen(shouldStartOpen);
    advancedToggle.addEventListener("click", () => {
      setAdvancedOpen(!advancedPanel.classList.contains("is-open"));
    });
  }
});
