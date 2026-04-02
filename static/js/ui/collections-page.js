document.addEventListener("DOMContentLoaded", () => {
  const shareButtons = Array.from(document.querySelectorAll("[data-share-collection]"));

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    const succeeded = document.execCommand("copy");
    document.body.removeChild(textarea);
    return succeeded;
  };

  shareButtons.forEach((button) => {
    const status = button.parentElement?.querySelector("[data-share-status]");
    let timer = null;
    button.addEventListener("click", async () => {
      const shareText = button.dataset.shareText || button.dataset.shareUrl || window.location.href;
      try {
        await copyText(shareText);
        if (status) {
          status.textContent = button.dataset.shareSuccess || "Copied";
          window.clearTimeout(timer);
          timer = window.setTimeout(() => {
            status.textContent = "";
          }, 2600);
        }
      } catch (error) {
        if (status) {
          status.textContent = button.dataset.shareFailure || "Unable to copy automatically";
          window.clearTimeout(timer);
          timer = window.setTimeout(() => {
            status.textContent = "";
          }, 2600);
        }
      }
    });
  });
});
