(function() {
  'use strict';
  var svgContainer = document.querySelector('.dag-section');

  // Phase 1: Segment / Full-path view toggle (works even without video)
  var btnSegment = document.getElementById('btn-segment-view');
  var btnFull = document.getElementById('btn-full-view');
  var segmentView = document.getElementById('dag-segment-view');
  var fullView = document.getElementById('dag-full-view');

  if (btnSegment && btnFull && segmentView && fullView) {
    window._dagSetView = function(mode) {
      if (mode === 'full') {
        segmentView.style.display = 'none';
        fullView.style.display = '';
        btnFull.classList.add('active');
        btnSegment.classList.remove('active');
      } else {
        segmentView.style.display = '';
        fullView.style.display = 'none';
        btnSegment.classList.add('active');
        btnFull.classList.remove('active');
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

  // Phase 2: Video synchronization (only when <video> element exists)
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
  var layerIndicator = document.getElementById('layer-indicator-name');

  // Build a lookup: node_id -> layer name (from SVG data attributes)
  var nodeToLayer = {};
  allNodes.forEach(function(n) {
    var nid = n.getAttribute('data-node');
    var lay = n.getAttribute('data-layer');
    if (nid && lay) nodeToLayer[nid] = lay;
  });

  // Receipt pane and overlay elements
  var receiptPane = document.querySelector('.receipt-pane');
  var overlayRects = document.querySelectorAll('.receipt-overlay rect');

  // Map sub-component timestamp keys to receipt field IDs, grouped by parent
  var fieldTimestamps = {};
  var fieldsByParent = {};
  Object.keys(TIMESTAMPS).forEach(function(k) {
    var parts = k.split('__');
    if (parts.length === 2 && TIMESTAMPS[k] !== null) {
      fieldTimestamps[k] = { field: parts[1], time: TIMESTAMPS[k], parent: parts[0] };
      if (!fieldsByParent[parts[0]]) fieldsByParent[parts[0]] = [];
      fieldsByParent[parts[0]].push(k);
    }
  });
  // Sort each parent's field keys by time
  Object.keys(fieldsByParent).forEach(function(p) {
    fieldsByParent[p].sort(function(a, b) { return fieldTimestamps[a].time - fieldTimestamps[b].time; });
  });

  // Debug overlay (toggle with 'd' key)
  var debugEl = null;
  var debugVisible = false;
  function ensureDebugEl() {
    if (!debugEl) {
      debugEl = document.createElement('div');
      debugEl.style.cssText = 'position:fixed;bottom:8px;right:8px;background:rgba(0,0,0,0.85);color:#0f0;font:11px/1.4 monospace;padding:8px 12px;border-radius:4px;z-index:9999;pointer-events:none;max-width:340px;white-space:pre';
      document.body.appendChild(debugEl);
    }
  }
  function updateDebug(videoTime, nodeId, activeField) {
    if (!debugVisible) return;
    ensureDebugEl();
    var lines = ['t=' + (videoTime !== undefined ? videoTime.toFixed(2) : '?') + 's'];
    lines.push('node=' + nodeId);
    lines.push('field=' + (activeField || '(none)'));
    // Show field timestamp ranges for the active TUI node
    var parentKeys = fieldsByParent[nodeId];
    if (parentKeys) {
      lines.push('---');
      for (var i = 0; i < parentKeys.length; i++) {
        var e = fieldTimestamps[parentKeys[i]];
        var marker = (e.field === activeField) ? '>' : ' ';
        var nextTime = (i + 1 < parentKeys.length) ? fieldTimestamps[parentKeys[i + 1]].time : null;
        var range = e.time.toFixed(2) + (nextTime ? '-' + nextTime.toFixed(2) : '+');
        lines.push(marker + ' ' + e.field + ' ' + range);
      }
    }
    debugEl.textContent = lines.join('\n');
  }

  function highlightReceiptField(nodeId, videoTime) {
    if (receiptPane) {
      var isReceiptNode = nodeId.indexOf('img_') === 0 ||
        nodeId.indexOf('nolbl_') === 0 ||
        nodeId.indexOf('tui_') === 0 ||
        nodeId.indexOf('lbl_') === 0;
      if (isReceiptNode) {
        receiptPane.classList.add('active');
      } else {
        receiptPane.classList.remove('active');
      }
    }
    var activeField = null;
    if (overlayRects.length > 0 && videoTime !== undefined) {
      var isTuiNode = nodeId.indexOf('tui_') === 0;
      if (isTuiNode) {
        // Only consider fields belonging to this specific TUI node
        var nodeFieldKeys = fieldsByParent[nodeId] || [];
        for (var i = 0; i < nodeFieldKeys.length; i++) {
          var entry = fieldTimestamps[nodeFieldKeys[i]];
          if (entry.time <= videoTime) activeField = entry.field;
        }
      }
      overlayRects.forEach(function(r) {
        r.classList.toggle('active', r.getAttribute('data-field') === activeField);
      });
    }
    updateDebug(videoTime, nodeId, activeField);
  }

  function highlightNode(nodeId) {
    allNodes.forEach(function(n) { n.classList.remove('active'); });
    clusters.forEach(function(c) { c.classList.remove('active-cluster'); });

    // Highlight the specific node in both SVG views
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

    // Update layer indicator
    if (layerIndicator) {
      layerIndicator.textContent = targetLayer.replace(/_/g, ' ') || nodeId;
    }

    // Highlight receipt image and field bounding boxes
    highlightReceiptField(nodeId, video ? video.currentTime : undefined);

    // Update currentIdx
    var idx = tsKeys.indexOf(nodeId);
    if (idx >= 0) currentIdx = idx;
  }

  // Sync: video time -> node highlight
  video.addEventListener('timeupdate', function() {
    var t = video.currentTime;
    var active = tsKeys[0];
    for (var i = 0; i < tsKeys.length; i++) {
      if (TIMESTAMPS[tsKeys[i]] <= t) active = tsKeys[i];
    }
    highlightNode(active);
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
    } else if (e.key === 'd') {
      debugVisible = !debugVisible;
      if (debugEl) debugEl.style.display = debugVisible ? '' : 'none';
      if (debugVisible) highlightNode(tsKeys[currentIdx]);
    }
  });

  // Click DAG node -> jump video (both views)
  svgContainer.querySelectorAll('.dag-node').forEach(function(node) {
    node.addEventListener('click', function() {
      var nid = node.getAttribute('data-node');
      if (nid && TIMESTAMPS[nid] !== undefined) {
        video.currentTime = TIMESTAMPS[nid];
        video.play();
      }
    });
  });

  // Initialize with first timestamped node
  highlightNode(tsKeys[0]);

  // Phase 3: Extend view toggle with video-aware behaviour
  if (typeof fullView !== 'undefined' && fullView) {
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
