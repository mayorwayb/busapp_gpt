<script defer src="{{ url_for('static', filename='js/dashboard.js') }}">
<!-- include at the bottom of each dashboard page -->
<script>
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggles = document.querySelectorAll(".js-toggle-sidebar");

  // restore collapsed state
  if (localStorage.getItem("sidebarCollapsed") === "true") {
    sidebar?.classList.add("collapsed");
  }

  toggles.forEach(btn => {
    btn.addEventListener("click", () => {
      sidebar?.classList.toggle("collapsed");
      localStorage.setItem("sidebarCollapsed", sidebar?.classList.contains("collapsed"));
    });
  });

  // highlight active via data-active on body (set in templates)
  const current = document.body.getAttribute("data-active");
  if (current) {
    const activeLink = document.querySelector(`.sidebar a[data-item="${current}"]`);
    if (activeLink) activeLink.classList.add("active");
  }
});
</script>
</script>
