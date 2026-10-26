document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("image-input");
  const selectedFile = document.getElementById("selected-file");
  if (fileInput && selectedFile) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      selectedFile.textContent = file ? `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)` : "";
      if (file && file.size > 5 * 1024 * 1024) {
        selectedFile.textContent = "This file is larger than 5 MB. Choose a smaller image.";
        selectedFile.classList.add("field-error");
        fileInput.value = "";
      } else {
        selectedFile.classList.remove("field-error");
      }
    });
  }
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "Are you sure?")) event.preventDefault();
    });
  });
});
