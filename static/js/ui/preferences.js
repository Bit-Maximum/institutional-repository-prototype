document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-auto-submit='true']").forEach((field) => {
    field.addEventListener("change", () => {
      const form = field.closest("form");
      if (form) {
        form.requestSubmit();
      }
    });
  });

  const disclosures = Array.from(document.querySelectorAll("[data-disclosure]"));
  const animationDuration = 220;

  const getTrigger = (item) => item.querySelector("[data-disclosure-trigger]");
  const getMenu = (item) => item.querySelector("[data-disclosure-menu]");
  const isOpen = (item) => item.classList.contains("is-open");

  const finalizeClose = (item) => {
    const menu = getMenu(item);
    const trigger = getTrigger(item);
    if (item.dataset.closeTimer) {
      window.clearTimeout(Number(item.dataset.closeTimer));
      delete item.dataset.closeTimer;
    }
    item.classList.remove("is-open", "is-closing");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
    if (menu) {
      menu.hidden = true;
    }
  };

  const closeDisclosure = (item) => {
    if (!item) return;
    const menu = getMenu(item);
    const trigger = getTrigger(item);
    if (!menu || menu.hidden) {
      finalizeClose(item);
      return;
    }
    item.classList.remove("is-open");
    item.classList.add("is-closing");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
    const timer = window.setTimeout(() => finalizeClose(item), animationDuration);
    item.dataset.closeTimer = String(timer);
  };

  const closeDisclosures = (except = null) => {
    disclosures.forEach((item) => {
      if (item !== except) {
        closeDisclosure(item);
      }
    });
  };

  const openDisclosure = (item) => {
    const menu = getMenu(item);
    const trigger = getTrigger(item);
    if (!menu || !trigger) return;
    closeDisclosures(item);
    if (item.dataset.closeTimer) {
      window.clearTimeout(Number(item.dataset.closeTimer));
      delete item.dataset.closeTimer;
    }
    menu.hidden = false;
    item.classList.remove("is-closing");
    requestAnimationFrame(() => {
      item.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
    });
  };

  disclosures.forEach((item) => {
    const trigger = getTrigger(item);
    if (!trigger) return;
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (isOpen(item)) {
        closeDisclosure(item);
      } else {
        openDisclosure(item);
      }
    });
  });

  const navToggle = document.querySelector("[data-nav-toggle]");
  const navDrawer = document.querySelector("[data-nav-drawer]");
  const mobileQuery = window.matchMedia("(max-width: 767px)");

  const closeMobileNav = () => {
    document.body.classList.remove("nav-open");
    if (navToggle) {
      navToggle.setAttribute("aria-expanded", "false");
    }
  };

  const openMobileNav = () => {
    document.body.classList.add("nav-open");
    document.body.classList.remove("header-hidden");
    if (navToggle) {
      navToggle.setAttribute("aria-expanded", "true");
    }
  };


  const siteHeader = document.querySelector(".site-header");
  let lastScrollY = window.scrollY;
  let ticking = false;

  const syncHeaderVisibility = () => {
    ticking = false;
    if (!siteHeader || mobileQuery.matches && document.body.classList.contains("nav-open")) {
      return;
    }

    const currentScrollY = window.scrollY;
    const scrollDelta = currentScrollY - lastScrollY;
    const passedThreshold = currentScrollY > 96;

    if (!passedThreshold || scrollDelta < -8) {
      document.body.classList.remove("header-hidden");
    } else if (scrollDelta > 10) {
      closeDisclosures();
      document.body.classList.add("header-hidden");
    }

    lastScrollY = currentScrollY;
  };

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(syncHeaderVisibility);
      ticking = true;
    }
  }, { passive: true });

  if (navToggle && navDrawer) {
    navToggle.addEventListener("click", () => {
      const drawerIsOpen = document.body.classList.contains("nav-open");
      if (drawerIsOpen) {
        closeMobileNav();
        closeDisclosures();
      } else {
        openMobileNav();
      }
    });

    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener("change", (event) => {
        if (!event.matches) {
          closeMobileNav();
        }
      });
    } else if (mobileQuery.addListener) {
      mobileQuery.addListener((event) => {
        if (!event.matches) {
          closeMobileNav();
        }
      });
    }
  }

  document.addEventListener("click", (event) => {
    const insideDisclosure = event.target.closest("[data-disclosure]");
    if (!insideDisclosure) {
      closeDisclosures();
    }

    if (mobileQuery.matches && navDrawer && navToggle) {
      const insideHeader = event.target.closest(".site-header__inner");
      if (!insideHeader) {
        closeMobileNav();
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDisclosures();
      closeMobileNav();
    }
  });
});
