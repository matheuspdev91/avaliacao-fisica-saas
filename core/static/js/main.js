(function () {
  var sidebar = document.getElementById('sidebar');
  var mainContent = document.getElementById('mainContent');
  var sidebarToggle = document.getElementById('sidebarToggle');

  function setSidebarState(collapsed) {
    if (!sidebar) return;
    if (collapsed) {
      sidebar.classList.add('collapsed');
      if (mainContent) mainContent.classList.add('collapsed');
    } else {
      sidebar.classList.remove('collapsed');
      if (mainContent) mainContent.classList.remove('collapsed');
    }
    try {
      localStorage.setItem('sidebarCollapsed', collapsed ? '1' : '0');
    } catch (e) {}
  }

  if (sidebar) {
    var stored = '';
    try { stored = localStorage.getItem('sidebarCollapsed'); } catch (e) {}
    if (stored === '1') setSidebarState(true);
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function () {
      if (!sidebar) return;
      var isCollapsed = sidebar.classList.contains('collapsed');
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle('mobile-open');
        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) overlay.classList.toggle('visible');
      } else {
        setSidebarState(!isCollapsed);
      }
    });
  }

  if (sidebar) {
    var overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.id = 'sidebarOverlay';
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function () {
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('visible');
    });

    var mobileMenuBtn = document.createElement('button');
    mobileMenuBtn.className = 'mobile-menu-btn';
    mobileMenuBtn.setAttribute('aria-label', 'Abrir menu');
    mobileMenuBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
    document.body.appendChild(mobileMenuBtn);

    mobileMenuBtn.addEventListener('click', function () {
      sidebar.classList.toggle('mobile-open');
      overlay.classList.toggle('visible');
    });
  }

  document.querySelectorAll('select.form-control, select').forEach(function (el) {
    if (!el.closest('.form-card') && !el.closest('form')) return;
    el.classList.add('form-control');
  });

  document.querySelectorAll('input[type=text], input[type=email], input[type=password], input[type=number], input[type=date], textarea, select').forEach(function (el) {
    if (!el.classList.contains('form-control') && !el.classList.contains('search-input') && !el.classList.contains('filter-chip')) {
      el.classList.add('form-control');
    }
  });
})();
