
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

  function applyZoom(pane) {
    var id = pane.getAttribute('data-zoom-id');
    var scale = scaleMap[id];
    // Use only the DIRECT .zoom-pane-inner child, not nested ones
    var inner = null;
    for (var i = 0; i < pane.children.length; i++) {
      if (pane.children[i].classList.contains('zoom-pane-inner')) {
        inner = pane.children[i]; break;
      }
    }
    if (inner) {
      inner.style.transform = 'scale(' + scale + ')';
      inner.style.transformOrigin = '0 0';
    }
    // Use only the direct zoom-indicator child
    var indicator = null;
    for (var j = 0; j < pane.children.length; j++) {
      if (pane.children[j].classList.contains('zoom-indicator')) {
        indicator = pane.children[j]; break;
      }
    }
    if (indicator) {
      indicator.textContent = Math.round(scale * 100) + '%';
    }
  }

  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    var id = selected.getAttribute('data-zoom-id');
    if (e.key === '=' || e.key === '+') {
      e.preventDefault();
      scaleMap[id] = Math.min(scaleMap[id] + 0.1, 3);
      applyZoom(selected);
    } else if (e.key === '-') {
      e.preventDefault();
      scaleMap[id] = Math.max(scaleMap[id] - 0.1, 0.3);
      applyZoom(selected);
    } else if (e.key === '0') {
      e.preventDefault();
      scaleMap[id] = 1;
      applyZoom(selected);
    }
  });

  // Alt+Left/Right: cycle which pane is selected
  document.addEventListener('keydown', function(e) {
    if (!e.altKey) return;
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

  // Mouse wheel zoom with Ctrl held — target innermost pane
  document.addEventListener('wheel', function(e) {
    if (!e.ctrlKey && !e.metaKey) return;
    var pane = closestPane(e.target);
    if (!pane) return;
    e.preventDefault();
    selectPane(pane);
    var id = pane.getAttribute('data-zoom-id');
    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    scaleMap[id] = Math.max(0.3, Math.min(3, scaleMap[id] + delta));
    applyZoom(pane);
  }, {passive: false});
})();
