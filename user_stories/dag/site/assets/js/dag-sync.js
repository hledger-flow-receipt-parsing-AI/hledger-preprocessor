(function() {
  'use strict';
  var svgContainer = document.querySelector('.dag-section');

  // Phase 1: Gray out unreachable nodes and edges (runs even without video)
  if (svgContainer && typeof NODE_PATH !== 'undefined') {
    svgContainer.querySelectorAll('.dag-node').forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && !NODE_PATH.includes(nid)) {
        n.classList.add('unreachable');
      }
    });
    // Hide edges where source or target is not in the story path
    svgContainer.querySelectorAll('.dag-edge').forEach(function(e) {
      var src = e.getAttribute('data-source');
      var tgt = e.getAttribute('data-target');
      if ((src && !NODE_PATH.includes(src)) || (tgt && !NODE_PATH.includes(tgt))) {
        e.classList.add('unreachable');
      }
    });
  }

  // Phase 2: Tree fold/unfold for path chip navigation
  // Auto-expand all children on page load
  document.querySelectorAll('.path-node-group').forEach(function(group) {
    var parentChip = group.querySelector('.path-node');
    var children = group.querySelector('.path-children');
    var indicator = group.querySelector('.expand-indicator');
    if (!parentChip || !children) return;

    // Start expanded
    children.classList.add('expanded');
    if (indicator) indicator.textContent = '\u25be';

    parentChip.addEventListener('click', function(e) {
      var isExpanded = children.classList.contains('expanded');
      if (isExpanded) {
        children.classList.remove('expanded');
        if (indicator) indicator.textContent = '\u25b8';
      } else {
        children.classList.add('expanded');
        if (indicator) indicator.textContent = '\u25be';
      }
      e.stopPropagation();
    });
  });

  // Phase 2b: Segment / Full-path view toggle (works even without video)
  var btnSegment = document.getElementById('btn-segment-view');
  var btnFull = document.getElementById('btn-full-view');
  var segmentView = document.getElementById('dag-segment-view');
  var fullView = document.getElementById('dag-full-view');

  if (btnSegment && btnFull && segmentView && fullView) {
    // Apply unreachable graying to the full-view SVG as well
    fullView.querySelectorAll('.dag-node').forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && NODE_PATH && !NODE_PATH.includes(nid)) n.classList.add('unreachable');
    });
    fullView.querySelectorAll('.dag-edge').forEach(function(e) {
      var src = e.getAttribute('data-source');
      var tgt = e.getAttribute('data-target');
      if (NODE_PATH && ((src && !NODE_PATH.includes(src)) || (tgt && !NODE_PATH.includes(tgt)))) {
        e.classList.add('unreachable');
      }
    });

    // Section layers for boxing in full-path view
    var sectionLayers = (typeof SECTION_LAYERS !== 'undefined') ? SECTION_LAYERS : [];
    var fullClusters = fullView.querySelectorAll('.dag-cluster');

    // _setView is defined here but called from Phase 3 when video is available
    window._dagSetView = function(mode) {
      if (mode === 'full') {
        segmentView.style.display = 'none';
        fullView.style.display = '';
        btnFull.classList.add('active');
        btnSegment.classList.remove('active');
        // Apply section boxing to primary layers
        fullClusters.forEach(function(c) {
          var layer = c.getAttribute('data-layer');
          if (layer && sectionLayers.indexOf(layer) >= 0) {
            c.classList.add('section-box');
          }
        });
      } else {
        segmentView.style.display = '';
        fullView.style.display = 'none';
        btnSegment.classList.add('active');
        btnFull.classList.remove('active');
        // Remove section boxing
        fullClusters.forEach(function(c) { c.classList.remove('section-box'); });
      }
      try { localStorage.setItem('dag-view-mode', mode); } catch(e) {}
    };

    btnSegment.addEventListener('click', function() { window._dagSetView('segment'); });
    btnFull.addEventListener('click', function() { window._dagSetView('full'); });

    // Restore saved preference
    try {
      var saved = localStorage.getItem('dag-view-mode');
      if (saved === 'full') window._dagSetView('full');
    } catch(e) {}
  }

  // Phase 3: Video synchronization (only when <video> element exists)
  var video = document.getElementById('demo-video');
  if (!video || !svgContainer || typeof TIMESTAMPS === 'undefined') return;

  // Build ordered list of parent-node timestamp keys (exclude sub-component keys)
  var tsKeys = Object.keys(TIMESTAMPS)
    .filter(function(k) { return TIMESTAMPS[k] !== null && k.indexOf('__') === -1; })
    .sort(function(a, b) { return TIMESTAMPS[a] - TIMESTAMPS[b]; });
  if (tsKeys.length === 0) return;

  var currentIdx = 0;
  var allNodes = svgContainer.querySelectorAll('.dag-node');
  var clusters = svgContainer.querySelectorAll('.dag-cluster');
  var pathChips = document.querySelectorAll('.path-node');
  var layerIndicator = document.getElementById('layer-indicator-name');

  // Build a lookup: node_id -> layer name (from SVG data attributes)
  var nodeToLayer = {};
  allNodes.forEach(function(n) {
    var nid = n.getAttribute('data-node');
    var lay = n.getAttribute('data-layer');
    if (nid && lay) nodeToLayer[nid] = lay;
  });

  function highlightNode(nodeId) {
    allNodes.forEach(function(n) { n.classList.remove('active'); });
    clusters.forEach(function(c) { c.classList.remove('active-cluster'); });
    pathChips.forEach(function(n) { n.classList.remove('active'); });
    document.querySelectorAll('.path-child.active').forEach(function(c) {
      c.classList.remove('active');
    });

    // Highlight the specific node in the SVG
    var targetLayer = nodeToLayer[nodeId] || '';
    allNodes.forEach(function(n) {
      if (n.getAttribute('data-node') === nodeId) {
        n.classList.add('active');
      }
    });

    // Highlight the cluster for this node's layer
    if (targetLayer) {
      clusters.forEach(function(c) {
        if (c.getAttribute('data-layer') === targetLayer) {
          c.classList.add('active-cluster');
        }
      });
    }

    // Highlight the matching path chip
    pathChips.forEach(function(chip) {
      if (chip.getAttribute('data-node') === nodeId) {
        chip.classList.add('active');
      }
    });

    // Update indicator
    if (layerIndicator) {
      layerIndicator.textContent = targetLayer.replace(/_/g, ' ') || nodeId;
    }

    // Update currentIdx
    var idx = tsKeys.indexOf(nodeId);
    if (idx >= 0) currentIdx = idx;
  }

  function highlightSubComponent(subKey) {
    document.querySelectorAll('.path-child.active').forEach(function(c) {
      c.classList.remove('active');
    });
    var el = document.querySelector('.path-child[data-sub="' + subKey + '"]');
    if (el) el.classList.add('active');
  }

  // Sync: video time -> node highlight (+ sub-component highlight)
  video.addEventListener('timeupdate', function() {
    var t = video.currentTime;
    var active = tsKeys[0];
    for (var i = 0; i < tsKeys.length; i++) {
      if (TIMESTAMPS[tsKeys[i]] <= t) active = tsKeys[i];
    }
    highlightNode(active);

    // Find the best matching sub-component for current time
    var bestSub = null;
    var bestSubTs = -1;
    var prefix = active + '__';
    Object.keys(TIMESTAMPS).forEach(function(k) {
      if (k.indexOf(prefix) === 0 && TIMESTAMPS[k] <= t && TIMESTAMPS[k] > bestSubTs) {
        bestSub = k;
        bestSubTs = TIMESTAMPS[k];
      }
    });
    if (bestSub) highlightSubComponent(bestSub);
  });

  // Keyboard: Up/Down jump between parent timestamped nodes
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowDown' || e.key === 'j') {
      e.preventDefault();
      currentIdx = Math.min(currentIdx + 1, tsKeys.length - 1);
      video.currentTime = TIMESTAMPS[tsKeys[currentIdx]];
      video.play();
    } else if (e.key === 'ArrowUp' || e.key === 'k') {
      e.preventDefault();
      currentIdx = Math.max(currentIdx - 1, 0);
      video.currentTime = TIMESTAMPS[tsKeys[currentIdx]];
      video.play();
    } else if (e.key === ' ' && e.target === document.body) {
      e.preventDefault();
      if (video.paused) video.play();
      else video.pause();
    }
  });

  // Click DAG node -> jump video
  allNodes.forEach(function(node) {
    node.addEventListener('click', function() {
      var nid = node.getAttribute('data-node');
      if (nid && TIMESTAMPS[nid] !== undefined) {
        video.currentTime = TIMESTAMPS[nid];
        video.play();
      }
    });
  });

  // Click parent path chip -> jump video + toggle children
  document.querySelectorAll('.path-node-group .path-node').forEach(function(chip) {
    chip.addEventListener('click', function() {
      var nid = chip.getAttribute('data-node');
      if (nid && TIMESTAMPS[nid] !== undefined) {
        video.currentTime = TIMESTAMPS[nid];
        video.play();
      }
    });
  });

  // Click path chip (nodes without children) -> jump video
  document.querySelectorAll('.path-node:not(.path-node-group .path-node)').forEach(function(chip) {
    chip.addEventListener('click', function() {
      var nid = chip.getAttribute('data-node');
      if (nid && TIMESTAMPS[nid] !== undefined) {
        video.currentTime = TIMESTAMPS[nid];
        video.play();
      }
    });
  });

  // Click child chip -> jump video to sub-timestamp
  document.querySelectorAll('.path-child').forEach(function(child) {
    child.addEventListener('click', function(e) {
      var subKey = child.getAttribute('data-sub');
      if (subKey && TIMESTAMPS[subKey] !== undefined) {
        video.currentTime = TIMESTAMPS[subKey];
        video.play();
      }
      e.stopPropagation();
    });
  });

  // Initialize with first timestamped node
  highlightNode(tsKeys[0]);

  // Phase 5: Extend view toggle with video-aware behaviour
  if (typeof fullView !== 'undefined' && fullView) {
    // Wire click-to-seek on full-view DAG nodes
    fullView.querySelectorAll('.dag-node').forEach(function(node) {
      node.addEventListener('click', function() {
        var nid = node.getAttribute('data-node');
        if (nid && TIMESTAMPS[nid] !== undefined) {
          video.currentTime = TIMESTAMPS[nid];
          video.play();
        }
      });
    });

    // Enhance _dagSetView with highlight re-binding
    var origSetView = window._dagSetView;
    window._dagSetView = function(mode) {
      origSetView(mode);
      var activeView = mode === 'full' ? fullView : segmentView;
      allNodes = activeView.querySelectorAll('.dag-node');
      clusters = activeView.querySelectorAll('.dag-cluster');
      nodeToLayer = {};
      allNodes.forEach(function(n) {
        var nid = n.getAttribute('data-node');
        var lay = n.getAttribute('data-layer');
        if (nid && lay) nodeToLayer[nid] = lay;
      });
      if (tsKeys.length > 0) highlightNode(tsKeys[currentIdx]);
    };

    // Re-apply saved preference now that video highlight works
    try {
      var saved = localStorage.getItem('dag-view-mode');
      if (saved === 'full') window._dagSetView('full');
    } catch(e) {}
  }
})();
