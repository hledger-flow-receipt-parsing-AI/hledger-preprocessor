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
