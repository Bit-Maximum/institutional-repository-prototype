document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-editor-root]");
  if (!root) return;

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

  const allInstances = [];
  const enhanceSelects = Array.from(document.querySelectorAll("select[data-enhance-editor-select='true']"));
  const components = new Map();
  const csrfToken = root.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";
  const createEndpoint = root.dataset.dictionaryCreateEndpoint || "";

  const progressCount = document.querySelector("[data-editor-progress-count]");
  const progressValue = document.querySelector("[data-editor-progress-value]");
  const progressBar = document.querySelector(".editor-progress__bar");
  const progressItems = Array.from(document.querySelectorAll("[data-progress-key]"));

  const modal = document.getElementById("editor-create-modal");
  const modalForm = document.getElementById("editor-create-modal-form");
  const modalFieldName = document.getElementById("editor-create-field-name");
  const modalValueInput = document.getElementById("editor-create-value");
  const modalTitle = document.getElementById("editor-create-modal-title");
  const modalDescription = document.getElementById("editor-create-modal-description");
  const modalStatus = document.getElementById("editor-create-modal-status");

  const i18n = {
    defaultEntityLabel: root.dataset.i18nDefaultEntityLabel || "элемент",
    createTitlePrefix: root.dataset.i18nCreateTitlePrefix || "Добавить",
    createDescription: root.dataset.i18nCreateDescription || "Новый элемент сразу появится в списке и будет выбран в карточке издания.",
    createButtonPrefix: root.dataset.i18nCreateButtonPrefix || "Добавить",
    createInputRequired: root.dataset.i18nCreateInputRequired || "Введите значение перед добавлением.",
    createSaving: root.dataset.i18nCreateSaving || "Сохраняем…",
    createFailed: root.dataset.i18nCreateFailed || "Не удалось добавить значение.",
  };

  const openModal = (instance, initialValue) => {
    if (!modal || !modalForm || !modalFieldName || !modalValueInput) return;
    modal.hidden = false;
    modal.dataset.currentSelectName = instance.select.name;
    modalFieldName.value = instance.select.name;
    modalValueInput.value = initialValue || "";
    modalStatus.textContent = "";
    const entityLabel = instance.select.dataset.createEntityLabel || instance.select.dataset.placeholder || i18n.defaultEntityLabel;
    if (modalTitle) modalTitle.textContent = `${i18n.createTitlePrefix} ${entityLabel}`;
    if (modalDescription) modalDescription.textContent = i18n.createDescription;
    document.body.classList.add("has-editor-modal");
    window.requestAnimationFrame(() => {
      if (typeof modalValueInput.focus === "function") {
        try {
          modalValueInput.focus({ preventScroll: true });
        } catch (error) {
          modalValueInput.focus();
        }
      }
    });
  };

  const closeModal = () => {
    if (!modal) return;
    modal.hidden = true;
    modal.dataset.currentSelectName = "";
    modalStatus && (modalStatus.textContent = "");
    document.body.classList.remove("has-editor-modal");
  };

  const closeAll = (except = null) => {
    allInstances.forEach((instance) => {
      if (instance !== except) instance.close();
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
    element.classList.remove("is-closing");
    window.requestAnimationFrame(() => element.classList.add(className));
  };

  const refreshProgress = () => {
    const checks = {
      title: Boolean(document.getElementById("id_title")?.value?.trim()),
      source_material: Boolean(document.getElementById("id_publication_format_link")?.value?.trim()) || Boolean(document.getElementById("id_file")?.files?.length) || root.dataset.hasExistingFile === "true",
      publication_year: Boolean(document.getElementById("id_publication_year")?.value?.trim()),
      language: Boolean(document.getElementById("id_language")?.value),
      publication_subtype: Boolean(document.getElementById("id_publication_subtype")?.value),
      authors: Array.from(document.getElementById("id_authors")?.options || []).some((option) => option.selected),
      contents: Boolean(document.getElementById("id_contents")?.value?.trim()),
    };
    const total = Object.keys(checks).length;
    const filled = Object.values(checks).filter(Boolean).length;
    const percent = total ? Math.round((filled / total) * 100) : 0;
    if (progressCount) progressCount.textContent = `${filled}/${total}`;
    if (progressValue) progressValue.style.width = `${percent}%`;
    if (progressBar) progressBar.setAttribute("aria-valuenow", String(percent));
    progressItems.forEach((item) => {
      const key = item.dataset.progressKey;
      const complete = Boolean(checks[key]);
      item.classList.toggle("is-complete", complete);
      const marker = item.querySelector(".editor-progress__marker");
      if (marker) marker.textContent = complete ? "✓" : "•";
    });
  };

  const createComponent = (select) => {
    select.classList.add("search-select-native");
    if (select.name === "file") return null;
    const wrapper = document.createElement("div");
    wrapper.className = "filter-picker editor-filter-picker";
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
        <div class="editor-filter-picker__footer" hidden>
          <button type="button" class="chip-link editor-filter-picker__create"></button>
        </div>
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
    const createFooter = wrapper.querySelector(".editor-filter-picker__footer");
    const createButton = wrapper.querySelector(".editor-filter-picker__create");
    const placeholder = select.dataset.placeholder || select.closest(".editor-field")?.querySelector("label")?.textContent?.trim() || "";
    const noResultsLabel = select.dataset.noResultsLabel || "Совпадений не найдено";
    const selectedManyLabel = select.dataset.selectedManyLabel || placeholder;
    const isMultiple = select.multiple;
    const showSelectionChips = select.dataset.showSelectionChips !== "false";
    const allowCreate = select.dataset.allowCreate === "true" && Boolean(createEndpoint);
    const summaryMode = select.dataset.summaryMode || "auto";
    const entityLabel = select.dataset.createEntityLabel || placeholder;
    let latestQuery = "";

    search.placeholder = `${placeholder}…`;

    const instance = {
      select,
      wrapper,
      dropdown,
      optionsHost,
      search,
      open() {
        closeAll(instance);
        wrapper.classList.add("is-open");
        wrapper.closest(".editor-field")?.classList.add("is-filter-open");
        wrapper.closest(".card")?.classList.add("is-overlay-active");
        trigger.setAttribute("aria-expanded", "true");
        animateShow(dropdown, "is-open");
        window.requestAnimationFrame(() => search.focus());
      },
      close() {
        wrapper.classList.remove("is-open");
        wrapper.closest(".editor-field")?.classList.remove("is-filter-open");
        wrapper.closest(".card")?.classList.remove("is-overlay-active");
        trigger.setAttribute("aria-expanded", "false");
        animateHide(dropdown, "is-open", "is-closing");
        search.value = "";
        renderOptions();
      },
      toggle() {
        if (wrapper.classList.contains("is-open")) instance.close();
        else instance.open();
      },
      refresh() {
        renderSelection();
        renderOptions();
      },
      getSelectedValues() {
        return Array.from(select.options).filter((option) => option.selected).map((option) => String(option.value));
      },
    };

    const refreshCreateAction = (visibleOptions) => {
      if (!allowCreate) {
        createFooter.hidden = true;
        return;
      }
      const query = search.value.trim();
      latestQuery = query;
      const hasExact = Array.from(select.options).some((option) => option.textContent.trim().toLowerCase() === query.toLowerCase());
      if (!query || hasExact) {
        createFooter.hidden = true;
        return;
      }
      createFooter.hidden = false;
      createButton.textContent = `${i18n.createButtonPrefix} «${query}»`;
    };

    const renderSelection = () => {
      const selected = Array.from(select.options).filter((option) => option.selected);
      if (!selected.length) {
        triggerText.textContent = placeholder;
        triggerCount.hidden = true;
        selection.hidden = true;
        selection.innerHTML = "";
        return;
      }
      if (isMultiple) {
        const useCountSummary = summaryMode === "count" || selected.length > 1;
        triggerText.textContent = useCountSummary ? selectedManyLabel : selected[0].textContent.trim();
        triggerCount.hidden = false;
        triggerCount.textContent = String(selected.length);
      } else {
        triggerText.textContent = selected[0].textContent.trim();
        triggerCount.hidden = true;
      }
      if (!showSelectionChips || !isMultiple) {
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

    const renderOptions = () => {
      const query = search.value.trim().toLowerCase();
      const visibleOptions = Array.from(select.options).filter((option) => !query || option.textContent.toLowerCase().includes(query));
      if (!visibleOptions.length) {
        optionsHost.innerHTML = `<div class="filter-picker__empty">${escapeHtml(noResultsLabel)}</div>`;
        refreshCreateAction(visibleOptions);
        return;
      }
      optionsHost.innerHTML = visibleOptions.map((option) => {
        const optionLabel = option.textContent.trim();
        return `
        <button type="button" class="filter-picker__option${option.selected ? " is-selected" : ""}" data-filter-option-value="${escapeHtml(option.value)}" title="${escapeHtml(optionLabel)}">
          <span class="filter-picker__option-label">${escapeHtml(optionLabel)}</span>
          ${option.selected ? '<span class="filter-picker__option-mark" aria-hidden="true">✓</span>' : ""}
        </button>
      `;
      }).join("");
      refreshCreateAction(visibleOptions);
    };

    const setSelected = (value, selected) => {
      const option = Array.from(select.options).find((item) => String(item.value) === String(value));
      if (!option) return;
      option.selected = selected;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      instance.refresh();
      refreshProgress();
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      instance.toggle();
    });

    search.addEventListener("input", renderOptions);

    optionsHost.addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter-option-value]");
      if (!button) return;
      const value = button.dataset.filterOptionValue;
      const option = Array.from(select.options).find((item) => String(item.value) === String(value));
      if (!option) return;
      if (isMultiple) {
        setSelected(value, !option.selected);
      } else {
        Array.from(select.options).forEach((item) => {
          item.selected = String(item.value) === String(value);
        });
        select.dispatchEvent(new Event("change", { bubbles: true }));
        instance.refresh();
        refreshProgress();
        instance.close();
      }
    });

    selection.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-filter-chip-value]");
      if (!chip || !isMultiple) return;
      setSelected(chip.dataset.filterChipValue, false);
    });

    createButton?.addEventListener("click", () => openModal(instance, latestQuery));
    select.addEventListener("change", () => {
      instance.refresh();
      refreshProgress();
    });

    instance.refresh();
    components.set(select.name, instance);
    allInstances.push(instance);
  };

  enhanceSelects.forEach(createComponent);

  root.addEventListener("input", refreshProgress);
  root.addEventListener("change", refreshProgress);
  refreshProgress();

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".filter-picker") && !event.target.closest(".editor-modal__dialog")) {
      closeAll();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAll();
      if (!modal?.hidden) closeModal();
    }
  });

  modal?.querySelectorAll("[data-editor-modal-close]").forEach((button) => {
    button.addEventListener("click", closeModal);
  });

  modalForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const currentSelectName = modal?.dataset.currentSelectName || modalFieldName?.value;
    const instance = components.get(currentSelectName);
    if (!instance) return;
    const value = modalValueInput?.value?.trim() || "";
    if (!value) {
      if (modalStatus) modalStatus.textContent = i18n.createInputRequired;
      return;
    }
    if (modalStatus) modalStatus.textContent = i18n.createSaving;
    const payload = new URLSearchParams({ field: currentSelectName, value });
    try {
      const response = await fetch(createEndpoint, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: payload.toString(),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || i18n.createFailed);
      let option = Array.from(instance.select.options).find((item) => String(item.value) === String(data.id));
      if (!option) {
        option = new Option(data.label, data.id, false, true);
        instance.select.add(option);
      }
      if (instance.select.multiple) {
        option.selected = true;
      } else {
        Array.from(instance.select.options).forEach((item) => {
          item.selected = String(item.value) === String(data.id);
        });
      }
      instance.select.dispatchEvent(new Event("change", { bubbles: true }));
      instance.refresh();
      refreshProgress();
      closeModal();
    } catch (error) {
      if (modalStatus) modalStatus.textContent = error.message || i18n.createFailed;
    }
  });

  window.PublicationEditor = {
    refreshAll() {
      components.forEach((instance) => instance.refresh());
      refreshProgress();
    },
  };
});
