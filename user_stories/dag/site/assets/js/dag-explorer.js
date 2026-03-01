
(function() {
  'use strict';
  var explorer = document.querySelector('.dag-explorer');
  var svg = explorer && explorer.querySelector('svg');
  if (!explorer || !svg || typeof STORIES === 'undefined') return;

  var allNodes = explorer.querySelectorAll('.dag-node');
  var allEdges = explorer.querySelectorAll('.dag-edge');
  var clusters = explorer.querySelectorAll('.dag-cluster');
  var statusEl = document.getElementById('explorer-status');
  var counterEl = document.getElementById('explorer-counter');
  var titleEl = document.getElementById('explorer-title');
  var swatchEl = document.getElementById('explorer-swatch');
  var hintsEl = document.getElementById('explorer-hints');

  // --- State ---
  var scale = 1;
  var panX = 0, panY = 0;
  var storyIdx = -1;  // -1 = overview mode
  var ZOOM_STEP = 0.15;
  var MIN_ZOOM = 0.3;
  var MAX_ZOOM = 5;

  // Pan state for mouse drag
  var dragging = false, dragStartX = 0, dragStartY = 0, panStartX = 0, panStartY = 0;

  // --- Helpers ---
  function applyTransform() {
    svg.style.transform = 'translate(' + panX + 'px,' + panY + 'px) scale(' + scale + ')';
  }

  function contentBBox() {
    // Compute a bounding box from clusters and nodes only
    // (skipping the background polygon that spans the full viewBox).
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    var items = svg.querySelectorAll('.dag-cluster, .dag-node, .dag-edge');
    for (var i = 0; i < items.length; i++) {
      try {
        var b = items[i].getBBox();
        if (b.width > 0 && b.height > 0) {
          if (b.x < minX) minX = b.x;
          if (b.y < minY) minY = b.y;
          if (b.x + b.width > maxX) maxX = b.x + b.width;
          if (b.y + b.height > maxY) maxY = b.y + b.height;
        }
      } catch(e) {}
    }
    if (minX === Infinity) return svg.getBBox();
    return {x: minX, y: minY, width: maxX - minX, height: maxY - minY};
  }

  function resetView() {
    // Fit the DAG content (clusters + nodes) into the explorer container,
    // positioned at the top-left.  We use contentBBox() instead of
    // svg.getBBox() because the latter includes the invisible background
    // polygon that spans the entire viewBox.
    var bbox = contentBBox();
    var containerW = explorer.clientWidth;
    var containerH = explorer.clientHeight;
    if (bbox.width > 0 && bbox.height > 0 && containerW > 0 && containerH > 0) {
      var scaleH = containerH / bbox.height;
      var scaleW = containerW / bbox.width;
      scale = Math.min(scaleH, scaleW, 1.5);
      panX = -bbox.x * scale;
      panY = -bbox.y * scale;
    } else {
      scale = 1; panX = 0; panY = 0;
    }
    applyTransform();
  }

  function zoom(delta, cx, cy) {
    var oldScale = scale;
    scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, scale + delta));
    var ratio = scale / oldScale;
    panX = cx - ratio * (cx - panX);
    panY = cy - ratio * (cy - panY);
    applyTransform();
  }

  function storyNodeSet(story) {
    var s = {};
    (story.paths || []).forEach(function(p) {
      p.forEach(function(nid) { s[nid] = true; });
    });
    return s;
  }

  function layersForNodes(nodeSet) {
    var layers = {};
    allNodes.forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && nodeSet[nid]) {
        var lay = n.getAttribute('data-layer');
        if (lay) layers[lay] = true;
      }
    });
    return layers;
  }

  function clearHighlights() {
    allNodes.forEach(function(n) {
      n.classList.remove('dimmed', 'story-hl');
      n.querySelectorAll('polygon, ellipse, rect').forEach(function(el) {
        el.style.removeProperty('stroke');
      });
    });
    allEdges.forEach(function(e) { e.classList.remove('dimmed'); });
    clusters.forEach(function(c) { c.classList.remove('cluster-hl'); });
  }

  function highlightStory(idx) {
    clearHighlights();
    if (idx < 0 || idx >= STORIES.length) {
      statusEl.style.display = 'none';
      document.querySelectorAll('.sidebar li a.explorer-active').forEach(function(a) {
        a.classList.remove('explorer-active');
      });
      return;
    }
    var story = STORIES[idx];
    var ns = storyNodeSet(story);
    var ls = layersForNodes(ns);

    allNodes.forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && ns[nid]) {
        n.classList.add('story-hl');
        n.querySelectorAll('polygon, ellipse, rect').forEach(function(el) {
          el.style.stroke = story.colour;
        });
      } else {
        n.classList.add('dimmed');
      }
    });
    // Match edges by stroke colour — each story has a unique colour on its edges
    var storyColour = story.colour.toLowerCase();
    allEdges.forEach(function(e) {
      var path = e.querySelector('path');
      var poly = e.querySelector('polygon');
      var edgeColour = '';
      if (path) edgeColour = (path.getAttribute('stroke') || '').toLowerCase();
      if (!edgeColour && poly) edgeColour = (poly.getAttribute('stroke') || '').toLowerCase();
      if (edgeColour === storyColour) {
        // This edge belongs to the current story — keep visible
      } else {
        e.classList.add('dimmed');
      }
    });
    clusters.forEach(function(c) {
      if (ls[c.getAttribute('data-layer')]) c.classList.add('cluster-hl');
    });

    statusEl.style.display = '';
    counterEl.textContent = (idx + 1) + ' / ' + STORIES.length;
    titleEl.textContent = story.id + ' \u2014 ' + story.title;
    // Update swatch line with story colour + dash pattern
    var swLine = swatchEl.querySelector('line');
    if (swLine) {
      swLine.setAttribute('stroke', story.colour);
      var dashMap = {dashed: '5,3', dotted: '2,3', bold: '', solid: ''};
      var da = dashMap[story.pattern] || '';
      swLine.setAttribute('stroke-dasharray', da);
      swLine.setAttribute('stroke-width', story.pattern === 'bold' ? '4' : '2.5');
    }

    document.querySelectorAll('.sidebar li a.explorer-active').forEach(function(a) {
      a.classList.remove('explorer-active');
    });
    var sidebar = document.querySelector('.sidebar');
    document.querySelectorAll('.sidebar li a').forEach(function(a) {
      if (a.textContent.indexOf(story.id + ':') === 0) {
        a.classList.add('explorer-active');
        // Open parent <details> if collapsed so the link is visible
        var det = a.closest('details');
        if (det && !det.open) det.open = true;
        // Scroll only the sidebar, not the page
        var aRect = a.getBoundingClientRect();
        var sRect = sidebar.getBoundingClientRect();
        if (aRect.top < sRect.top) {
          sidebar.scrollTop += aRect.top - sRect.top;
        } else if (aRect.bottom > sRect.bottom) {
          sidebar.scrollTop += aRect.bottom - sRect.bottom;
        }
      }
    });
  }

  // --- Keyboard ---
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    // Let browser shortcuts (Ctrl+L, Ctrl+H, etc.) pass through
    if (e.ctrlKey || e.metaKey) return;

    var cx = explorer.clientWidth / 2;
    var cy = explorer.clientHeight / 2;

    switch (e.key) {
      case 'ArrowRight':
      case 'l':
        e.preventDefault();
        if (storyIdx < STORIES.length - 1) {
          storyIdx++;
          highlightStory(storyIdx);
        }
        break;

      case 'ArrowLeft':
      case 'h':
        e.preventDefault();
        if (storyIdx > 0) {
          storyIdx--;
          highlightStory(storyIdx);
        } else if (storyIdx === 0) {
          storyIdx = -1;
          highlightStory(-1);
        }
        break;

      case 'Escape':
        e.preventDefault();
        storyIdx = -1;
        highlightStory(-1);
        break;

      case 'Enter':
        e.preventDefault();
        if (storyIdx >= 0 && storyIdx < STORIES.length) {
          window.location.href = STORIES[storyIdx].url;
        }
        break;

      case '=':
      case '+':
        e.preventDefault();
        zoom(ZOOM_STEP, cx, cy);
        break;

      case '-':
        e.preventDefault();
        zoom(-ZOOM_STEP, cx, cy);
        break;

      case '0':
        e.preventDefault();
        resetView();
        break;
    }
  });

  // --- Mouse wheel zoom ---
  explorer.addEventListener('wheel', function(e) {
    e.preventDefault();
    var rect = explorer.getBoundingClientRect();
    var cx = e.clientX - rect.left;
    var cy = e.clientY - rect.top;
    var delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
    zoom(delta, cx, cy);
  }, { passive: false });

  // --- Mouse drag pan ---
  explorer.addEventListener('mousedown', function(e) {
    if (e.button !== 0) return;
    dragging = true;
    dragStartX = e.clientX; dragStartY = e.clientY;
    panStartX = panX; panStartY = panY;
  });
  window.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    panX = panStartX + (e.clientX - dragStartX);
    panY = panStartY + (e.clientY - dragStartY);
    applyTransform();
  });
  window.addEventListener('mouseup', function() { dragging = false; });

  // --- Click node -> select that story ---
  allNodes.forEach(function(node) {
    node.addEventListener('click', function(e) {
      var nid = node.getAttribute('data-node');
      if (!nid) return;
      for (var i = 0; i < STORIES.length; i++) {
        var ns = storyNodeSet(STORIES[i]);
        if (ns[nid]) {
          e.stopPropagation();
          storyIdx = i;
          highlightStory(i);
          return;
        }
      }
    });
  });

  // --- Sidebar link click -> highlight that story on DAG ---
  document.querySelectorAll('.sidebar li a').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var text = a.textContent;
      for (var i = 0; i < STORIES.length; i++) {
        if (text.indexOf(STORIES[i].id + ':') === 0) {
          e.preventDefault();
          storyIdx = i;
          highlightStory(i);
          return;
        }
      }
    });
  });

  // --- Init ---
  resetView();

  // Start with US-3.5 highlighted (full chain, most intuitive)
  var defaultIdx = -1;
  for (var di = 0; di < STORIES.length; di++) {
    if (STORIES[di].id === 'US-3.5') { defaultIdx = di; break; }
  }
  if (defaultIdx >= 0) {
    storyIdx = defaultIdx;
    highlightStory(storyIdx);
  } else {
    statusEl.style.display = 'none';
  }

  hintsEl.innerHTML =
    '<kbd>&#x2190;</kbd><kbd>&#x2192;</kbd> cycle stories \u00b7 ' +
    '<kbd>Enter</kbd> open \u00b7 ' +
    '<kbd>Esc</kbd> overview \u00b7 ' +
    '<kbd>+</kbd><kbd>-</kbd> zoom \u00b7 ' +
    '<kbd>0</kbd> reset \u00b7 scroll to zoom \u00b7 drag to pan';
})();
