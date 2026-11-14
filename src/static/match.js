
(function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';

  function findBoxByKey(host, side, key) {
    return host.querySelector('.match-box[data-side="' + side + '"][data-key="' + cssEscape(key) + '"]');
  }

  // Conservative CSS attribute-value escaper for the keys we use (alphanumeric +
  // a few separators). The data-key is set by the renderer from a slugged value,
  // so this is just a safety net.
  function cssEscape(s) {
    return String(s).replace(/(["\\])/g, '\\$1');
  }

  function rectMidpoints(box, hostRect) {
    var r = box.getBoundingClientRect();
    return {
      leftX: r.left - hostRect.left,
      rightX: r.right - hostRect.left,
      midY: (r.top + r.bottom) / 2 - hostRect.top
    };
  }

  function initGrid(host) {
    var svg = host.querySelector('.match-lines');
    var countEl = host.querySelector('.match-count');
    var clearBtn = host.querySelector('.match-clear');
    if (!svg) return;

    var leftBoxes = Array.prototype.slice.call(host.querySelectorAll('.match-box[data-side="L"]'));
    var rightBoxes = Array.prototype.slice.call(host.querySelectorAll('.match-box[data-side="R"]'));
    var leftTotal = leftBoxes.length;

    // connections: Map<leftKey, { rightKey, lineEl }>
    var connections = new Map();
    var leftActive = null;

    function updateCount() {
      if (!countEl) return;
      countEl.textContent = connections.size + ' / ' + leftTotal + ' lines drawn';
    }

    function setActive(box) {
      if (leftActive && leftActive !== box) leftActive.classList.remove('is-active');
      leftActive = box;
      if (box) box.classList.add('is-active');
    }

    function markConnected(box, on) {
      if (!box) return;
      box.classList.toggle('is-connected', !!on);
    }

    function rightStillTargeted(rightKey) {
      var found = false;
      connections.forEach(function (v) { if (v.rightKey === rightKey) found = true; });
      return found;
    }

    function placeLine(line, leftBox, rightBox) {
      var hostRect = host.getBoundingClientRect();
      var L = rectMidpoints(leftBox, hostRect);
      var R = rectMidpoints(rightBox, hostRect);
      line.setAttribute('x1', String(L.rightX));
      line.setAttribute('y1', String(L.midY));
      line.setAttribute('x2', String(R.leftX));
      line.setAttribute('y2', String(R.midY));
    }

    function ensureSvgViewport() {
      var rect = host.getBoundingClientRect();
      svg.setAttribute('width', String(rect.width));
      svg.setAttribute('height', String(rect.height));
      svg.setAttribute('viewBox', '0 0 ' + rect.width + ' ' + rect.height);
    }

    function drawConnection(leftKey, rightKey) {
      var leftBox = findBoxByKey(host, 'L', leftKey);
      var rightBox = findBoxByKey(host, 'R', rightKey);
      if (!leftBox || !rightBox) return;

      ensureSvgViewport();
      var line = document.createElementNS(SVG_NS, 'line');
      line.setAttribute('class', 'match-line');
      line.setAttribute('stroke', '#1e3a5f');
      line.setAttribute('stroke-width', '2.5');
      line.setAttribute('stroke-linecap', 'round');
      placeLine(line, leftBox, rightBox);
      line.addEventListener('click', function (e) {
        e.stopPropagation();
        removeConnection(leftKey);
      });
      svg.appendChild(line);
      return line;
    }

    function removeConnection(leftKey) {
      var c = connections.get(leftKey);
      if (!c) return;
      if (c.lineEl && c.lineEl.parentNode) c.lineEl.parentNode.removeChild(c.lineEl);
      connections.delete(leftKey);
      markConnected(findBoxByKey(host, 'L', leftKey), false);
      if (!rightStillTargeted(c.rightKey)) {
        markConnected(findBoxByKey(host, 'R', c.rightKey), false);
      }
      updateCount();
    }

    function setConnection(leftKey, rightKey) {
      var prev = connections.get(leftKey);
      if (prev) {
        if (prev.lineEl && prev.lineEl.parentNode) prev.lineEl.parentNode.removeChild(prev.lineEl);
        if (!rightStillTargeted(prev.rightKey) || prev.rightKey === rightKey) {
          markConnected(findBoxByKey(host, 'R', prev.rightKey), false);
        }
      }
      var line = drawConnection(leftKey, rightKey);
      connections.set(leftKey, { rightKey: rightKey, lineEl: line });
      markConnected(findBoxByKey(host, 'L', leftKey), true);
      markConnected(findBoxByKey(host, 'R', rightKey), true);
      updateCount();
    }

    function repositionAll() {
      ensureSvgViewport();
      connections.forEach(function (v, leftKey) {
        var leftBox = findBoxByKey(host, 'L', leftKey);
        var rightBox = findBoxByKey(host, 'R', v.rightKey);
        if (leftBox && rightBox && v.lineEl) placeLine(v.lineEl, leftBox, rightBox);
      });
    }

    leftBoxes.forEach(function (box) {
      box.addEventListener('click', function (e) {
        e.preventDefault();
        if (leftActive === box) {
          setActive(null);
        } else {
          setActive(box);
        }
      });
    });

    rightBoxes.forEach(function (box) {
      box.addEventListener('click', function (e) {
        e.preventDefault();
        if (!leftActive) return;
        var leftKey = leftActive.dataset.key;
        var rightKey = box.dataset.key;
        setConnection(leftKey, rightKey);
        setActive(null);
      });
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function (e) {
        e.preventDefault();
        Array.prototype.slice.call(connections.keys()).forEach(removeConnection);
        setActive(null);
      });
    }

    window.addEventListener('resize', repositionAll);
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(repositionAll);
      ro.observe(host);
    }
    // Reposition once after the initial layout settles (font loads, etc.).
    setTimeout(repositionAll, 0);
    ensureSvgViewport();
    updateCount();
  }

  function initAll() {
    Array.prototype.forEach.call(document.querySelectorAll('.match-grid'), initGrid);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
