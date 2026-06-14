
(function() {
  'use strict';
  var panes = document.querySelectorAll('.zoom-pane');
  if (!panes.length) return;

  var selected = null;
  var scaleMap = {};

  // Independent mode state per grid: stores pixel widths
  var indepWidths = new WeakMap();

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

    // Add resize buttons for panes inside a video-dag-row grid
    if (pane.closest('.video-dag-row')) {
      var btnGroup = document.createElement('span');
      btnGroup.className = 'zoom-resize-buttons';

      var btnShrink = document.createElement('button');
      btnShrink.className = 'zoom-resize-btn';
      btnShrink.textContent = '\u2212';
      btnShrink.title = 'Shrink this pane only';
      btnShrink.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        indepResize(pane, -1);
      });

      var btnGrow = document.createElement('button');
      btnGrow.className = 'zoom-resize-btn';
      btnGrow.textContent = '+';
      btnGrow.title = 'Grow this pane only';
      btnGrow.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        indepResize(pane, +1);
      });

      var btnReset = document.createElement('button');
      btnReset.className = 'zoom-resize-btn';
      btnReset.textContent = '\u21ba';
      btnReset.title = 'Reset pane size';
      btnReset.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        resetAll(pane);
      });

      btnGroup.appendChild(btnShrink);
      btnGroup.appendChild(btnGrow);
      btnGroup.appendChild(btnReset);
      pane.appendChild(btnGroup);
    }
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

  function clearTransforms(pane) {
    var inner = pane.querySelector('.zoom-pane-inner');
    if (inner) {
      inner.style.transform = '';
      inner.style.transformOrigin = '';
      inner.style.width = '';
      inner.style.height = '';
    }
    pane.style.zoom = '';
  }

  function getIndicator(pane) {
    for (var j = 0; j < pane.children.length; j++) {
      if (pane.children[j].classList.contains('zoom-indicator')) {
        return pane.children[j];
      }
    }
    return null;
  }

  // Independent resize using pixel widths.
  // direction: -1 = shrink, +1 = grow
  var STEP_PX = 40;

  function indepResize(pane, direction) {
    var grid = pane.closest('.video-dag-row');
    if (!grid) return;

    var vp = grid.querySelector('.video-section.zoom-pane');
    var dp = grid.querySelector('.dag-section.zoom-pane');
    if (!vp || !dp) return;

    // Clear any coupled-mode zoom first
    clearTransforms(vp);
    clearTransforms(dp);
    scaleMap[vp.getAttribute('data-zoom-id')] = 1;
    scaleMap[dp.getAttribute('data-zoom-id')] = 1;

    // Snapshot current widths if not already in independent mode
    var w = indepWidths.get(grid);
    if (!w) {
      w = {
        video: vp.getBoundingClientRect().width,
        dag: dp.getBoundingClientRect().width
      };
      indepWidths.set(grid, w);
    }

    // Adjust only the target pane
    var isVideo = pane === vp;
    var key = isVideo ? 'video' : 'dag';
    w[key] = Math.max(100, w[key] + direction * STEP_PX);

    grid.style.gridTemplateColumns = w.video + 'px ' + w.dag + 'px';

    // Update indicators
    var vInd = getIndicator(vp);
    var dInd = getIndicator(dp);
    if (vInd) vInd.textContent = Math.round(w.video) + 'px';
    if (dInd) dInd.textContent = Math.round(w.dag) + 'px';
  }

  function resetAll(pane) {
    var grid = pane.closest('.video-dag-row');
    if (grid) {
      grid.style.gridTemplateColumns = '';
      indepWidths.delete(grid);
    }

    var vp = grid && grid.querySelector('.video-section.zoom-pane');
    var dp = grid && grid.querySelector('.dag-section.zoom-pane');

    if (vp) { clearTransforms(vp); scaleMap[vp.getAttribute('data-zoom-id')] = 1; }
    if (dp) { clearTransforms(dp); scaleMap[dp.getAttribute('data-zoom-id')] = 1; }

    var vInd = vp && getIndicator(vp);
    var dInd = dp && getIndicator(dp);
    if (vInd) vInd.textContent = '100%';
    if (dInd) dInd.textContent = '100%';
  }

  function applyCoupledZoom(pane) {
    var id = pane.getAttribute('data-zoom-id');
    var scale = scaleMap[id];

    var inner = pane.querySelector('.zoom-pane-inner');
    if (inner) {
      inner.style.transform = '';
      inner.style.transformOrigin = '';
      inner.style.width = '';
      inner.style.height = '';
    }
    pane.style.zoom = scale;

    var grid = pane.closest('.video-dag-row');
    if (grid) {
      indepWidths.delete(grid);
      var videoScale = 1, dagScale = 1;
      var vp = grid.querySelector('.video-section.zoom-pane');
      var dp = grid.querySelector('.dag-section.zoom-pane');
      if (vp) videoScale = scaleMap[vp.getAttribute('data-zoom-id')] || 1;
      if (dp) dagScale = scaleMap[dp.getAttribute('data-zoom-id')] || 1;
      grid.style.gridTemplateColumns = videoScale + 'fr ' + dagScale + 'fr';
    }
    var indicator = getIndicator(pane);
    if (indicator) {
      indicator.textContent = Math.round(scale * 100) + '%';
    }
  }

  // Ctrl+/- = coupled zoom
  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.altKey || e.shiftKey) return;

    var id = selected.getAttribute('data-zoom-id');

    if (e.key === '=' || e.key === '+') {
      e.preventDefault();
      scaleMap[id] = Math.min(scaleMap[id] + 0.1, 3);
      applyCoupledZoom(selected);
    } else if (e.key === '-') {
      e.preventDefault();
      scaleMap[id] = Math.max(scaleMap[id] - 0.1, 0.3);
      applyCoupledZoom(selected);
    } else if (e.key === '0') {
      e.preventDefault();
      resetAll(selected);
    }
  });

  // Independent resize: , (or <) to shrink, . (or >) to grow, / to reset.
  // Also [ ] \ as alternatives.
  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.target.tagName === 'BUTTON') return;

    var inGrid = !!selected.closest('.video-dag-row');
    if (!inGrid) return;

    if (e.key === ',' || e.key === '<' || e.key === '[') {
      e.preventDefault();
      indepResize(selected, -1);
    } else if (e.key === '.' || e.key === '>' || e.key === ']') {
      e.preventDefault();
      indepResize(selected, +1);
    } else if (e.key === '/' || e.key === '\\') {
      e.preventDefault();
      resetAll(selected);
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

  // Mouse wheel zoom — Ctrl+scroll = coupled
  document.addEventListener('wheel', function(e) {
    if (!e.ctrlKey && !e.metaKey) return;
    var pane = closestPane(e.target);
    if (!pane) return;
    e.preventDefault();
    selectPane(pane);
    var id = pane.getAttribute('data-zoom-id');
    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    scaleMap[id] = Math.max(0.3, Math.min(3, scaleMap[id] + delta));
    applyCoupledZoom(pane);
  }, {passive: false});
})();
