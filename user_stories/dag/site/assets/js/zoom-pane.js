
(function() {
  'use strict';
  var panes = document.querySelectorAll('.zoom-pane');
  if (!panes.length) return;

  var selected = null;
  var scaleMap = {};

  // Find the innermost zoom-pane for a given element
  function closestPane(el) {
    while (el) {
      if (el.classList && el.classList.contains('zoom-pane')
          && el.getAttribute('data-zoom-id')) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  panes.forEach(function(pane) {
    var id = pane.getAttribute('data-zoom-id');
    if (!id) return;
    scaleMap[id] = 1;

    // Add zoom indicator
    var indicator = document.createElement('span');
    indicator.className = 'zoom-indicator';
    indicator.textContent = '100%';
    pane.appendChild(indicator);
  });

  // Single document-level listener picks the innermost zoom-pane
  document.addEventListener('mousedown', function(e) {
    var pane = closestPane(e.target);
    if (pane) selectPane(pane);
  });

  function selectPane(pane) {
    if (selected === pane) return;
    panes.forEach(function(p) { p.classList.remove('zoom-selected'); });
    pane.classList.add('zoom-selected');
    selected = pane;
  }

  // soloMode=true: scale the pane content without rebalancing the grid columns
  function applyZoom(pane, soloMode) {
    var id = pane.getAttribute('data-zoom-id');
    var scale = scaleMap[id];

    if (soloMode) {
      // Scale only the inner content via CSS transform, keep grid layout unchanged
      var inner = pane.querySelector('.zoom-pane-inner');
      if (inner) {
        inner.style.transform = 'scale(' + scale + ')';
        inner.style.transformOrigin = 'top left';
        inner.style.width = (100 / scale) + '%';
        inner.style.height = 'auto';
      }
      pane.style.zoom = '';
    } else {
      // Reset any solo-mode transform
      var inner = pane.querySelector('.zoom-pane-inner');
      if (inner) {
        inner.style.transform = '';
        inner.style.transformOrigin = '';
        inner.style.width = '';
        inner.style.height = '';
      }
      // CSS zoom changes the element's rendered size in the layout
      pane.style.zoom = scale;

      // If inside a video-dag-row grid, rebuild column ratios so both
      // panes can grow/shrink independently based on their own zoom level.
      var grid = pane.closest('.video-dag-row');
      if (grid) {
        var videoScale = 1, dagScale = 1;
        var vp = grid.querySelector('.video-section.zoom-pane');
        var dp = grid.querySelector('.dag-section.zoom-pane');
        if (vp) videoScale = scaleMap[vp.getAttribute('data-zoom-id')] || 1;
        if (dp) dagScale = scaleMap[dp.getAttribute('data-zoom-id')] || 1;
        grid.style.gridTemplateColumns = videoScale + 'fr ' + dagScale + 'fr';
      }
    }

    // Update zoom indicator
    var indicator = null;
    for (var j = 0; j < pane.children.length; j++) {
      if (pane.children[j].classList.contains('zoom-indicator')) {
        indicator = pane.children[j]; break;
      }
    }
    if (indicator) {
      indicator.textContent = Math.round(scale * 100) + '%' + (soloMode ? ' solo' : '');
    }
  }

  // Track which mode each pane is in
  var modeMap = {};

  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    var id = selected.getAttribute('data-zoom-id');
    var soloMode = e.altKey;

    if (e.key === '=' || e.key === '+') {
      e.preventDefault();
      scaleMap[id] = Math.min(scaleMap[id] + 0.1, 3);
      modeMap[id] = soloMode ? 'solo' : 'coupled';
      applyZoom(selected, soloMode);
    } else if (e.key === '-') {
      e.preventDefault();
      scaleMap[id] = Math.max(scaleMap[id] - 0.1, 0.3);
      modeMap[id] = soloMode ? 'solo' : 'coupled';
      applyZoom(selected, soloMode);
    } else if (e.key === '0') {
      e.preventDefault();
      scaleMap[id] = 1;
      modeMap[id] = 'coupled';
      applyZoom(selected, false);
    }
  });

  // Alt+Left/Right: cycle which pane is selected
  document.addEventListener('keydown', function(e) {
    if (!e.altKey) return;
    if (e.ctrlKey || e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    var arr = Array.prototype.slice.call(panes);
    if (!arr.length) return;
    var cur = selected ? arr.indexOf(selected) : -1;
    var next;
    if (e.key === 'ArrowRight') {
      next = (cur + 1) % arr.length;
    } else {
      next = (cur - 1 + arr.length) % arr.length;
    }
    selectPane(arr[next]);
    arr[next].scrollIntoView({behavior: 'smooth', block: 'nearest'});
  });

  // Mouse wheel zoom — Ctrl+scroll = coupled, Ctrl+Alt+scroll = solo
  document.addEventListener('wheel', function(e) {
    if (!e.ctrlKey && !e.metaKey) return;
    var pane = closestPane(e.target);
    if (!pane) return;
    e.preventDefault();
    selectPane(pane);
    var id = pane.getAttribute('data-zoom-id');
    var soloMode = e.altKey;
    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    scaleMap[id] = Math.max(0.3, Math.min(3, scaleMap[id] + delta));
    modeMap[id] = soloMode ? 'solo' : 'coupled';
    applyZoom(pane, soloMode);
  }, {passive: false});
})();
