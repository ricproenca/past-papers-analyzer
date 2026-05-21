
(function () {
  'use strict';

  if (typeof joint === 'undefined' || !joint.dia) {
    console.warn('[circuit] JointJS not loaded; circuit editors disabled.');
    function showLoadError() {
      Array.prototype.forEach.call(document.querySelectorAll('.circuit-editor'), function (host) {
        var paper = host.querySelector('.circuit-paper');
        if (paper && !paper.firstChild) {
          paper.innerHTML =
            '<p style="padding:1rem;color:#b91c1c;font-size:.85rem;">' +
            'JointJS failed to load from CDN. Check your network or replace the ' +
            '<code>@joint/core</code> CDN URL in <code>renderer.py</code>.' +
            '</p>';
        }
      });
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showLoadError);
    } else {
      showLoadError();
    }
    return;
  }

  var dia = joint.dia;
  var shapes = joint.shapes;

  // Gate geometry — body path data in a 60×40 (or 70×40 for OR-family) box.
  // Port `args.x/y` give the port circle's absolute position within the element
  // because we use position: { name: 'absolute' } on each group.

  var GATES = {
    AND: {
      label: 'AND', inputs: 2,
      width: 60, height: 40,
      // D-shape: flat left, semicircle right
      path: 'M 2 2 L 30 2 A 18 18 0 0 1 30 38 L 2 38 Z',
      labelX: 22, labelY: 20,
      in1Y: 12, in2Y: 28, outY: 20
    },
    OR: {
      label: 'OR', inputs: 2,
      width: 70, height: 40,
      // Curved back, pointed front
      path: 'M 2 2 Q 22 2 50 20 Q 22 38 2 38 Q 16 20 2 2 Z',
      labelX: 26, labelY: 20,
      in1Y: 12, in2Y: 28, outY: 20
    },
    NOT: {
      label: 'NOT', inputs: 1,
      width: 60, height: 40,
      path: 'M 2 2 L 44 20 L 2 38 Z',
      labelX: 18, labelY: 20,
      bubble: true, bubbleX: 48, bubbleY: 20,
      in1Y: 20, outY: 20
    },
    NAND: {
      label: 'NAND', inputs: 2,
      width: 66, height: 40,
      path: 'M 2 2 L 30 2 A 18 18 0 0 1 30 38 L 2 38 Z',
      labelX: 22, labelY: 20,
      bubble: true, bubbleX: 52, bubbleY: 20,
      in1Y: 12, in2Y: 28, outY: 20
    },
    NOR: {
      label: 'NOR', inputs: 2,
      width: 76, height: 40,
      path: 'M 2 2 Q 22 2 50 20 Q 22 38 2 38 Q 16 20 2 2 Z',
      labelX: 26, labelY: 20,
      bubble: true, bubbleX: 56, bubbleY: 20,
      in1Y: 12, in2Y: 28, outY: 20
    },
    XOR: {
      label: 'XOR', inputs: 2,
      width: 74, height: 40,
      // OR body shifted right by 4 so the XOR curve sits in front
      path: 'M 6 2 Q 26 2 54 20 Q 26 38 6 38 Q 20 20 6 2 Z',
      extraPath: 'M 0 2 Q 14 20 0 38',
      labelX: 30, labelY: 20,
      in1Y: 12, in2Y: 28, outY: 20
    }
  };

  // Override per-gate port x positions (must come after width is known)
  Object.keys(GATES).forEach(function (k) {
    var g = GATES[k];
    g.in1X = (k === 'XOR') ? 0 : 2;
    g.in2X = g.in1X;
    g.outX = g.width - 2;
  });

  // Build the Element classes
  var GateClasses = {};
  Object.keys(GATES).forEach(function (k) {
    var g = GATES[k];
    // Patch each port item with absolute x,y inside the element
    var def = Object.assign({}, g);
    GateClasses[k] = makeGateWithPorts(k, def);
  });

  function makeGateWithPorts(typeName, def) {
    var portItems = [];
    if (def.inputs >= 1) portItems.push({ id: 'in1', group: 'in', args: { x: def.in1X, y: def.in1Y } });
    if (def.inputs >= 2) portItems.push({ id: 'in2', group: 'in', args: { x: def.in2X, y: def.in2Y } });
    portItems.push({ id: 'out', group: 'out', args: { x: def.outX, y: def.outY } });

    var bodyAttrs = { d: def.path, fill: '#fff', stroke: '#1f2937', strokeWidth: 1.6 };
    var labelAttrs = {
      text: def.label,
      x: def.labelX, y: def.labelY,
      textAnchor: 'middle', textVerticalAnchor: 'middle',
      fontSize: 10, fontWeight: '600', fill: '#1f2937',
      fontFamily: 'system-ui, sans-serif',
      pointerEvents: 'none'
    };
    var markup = [{ tagName: 'path', selector: 'body' }];
    var attrs = { body: bodyAttrs, label: labelAttrs };
    if (def.extraPath) {
      markup.push({ tagName: 'path', selector: 'extra' });
      attrs.extra = { d: def.extraPath, fill: 'none', stroke: '#1f2937', strokeWidth: 1.6 };
    }
    if (def.bubble) {
      markup.push({ tagName: 'circle', selector: 'bubble' });
      attrs.bubble = {
        cx: def.bubbleX, cy: def.bubbleY, r: 3.5,
        fill: '#fff', stroke: '#1f2937', strokeWidth: 1.6
      };
    }
    markup.push({ tagName: 'text', selector: 'label' });

    return dia.Element.define('logic.' + typeName, {
      size: { width: def.width, height: def.height },
      attrs: attrs,
      ports: {
        groups: {
          in: {
            position: { name: 'absolute' },
            attrs: {
              portCircle: {
                r: 4, magnet: 'passive',
                fill: '#fff', stroke: '#1e3a5f', strokeWidth: 1.5
              }
            },
            markup: [{ tagName: 'circle', selector: 'portCircle' }]
          },
          out: {
            position: { name: 'absolute' },
            attrs: {
              portCircle: {
                r: 4, magnet: true,
                fill: '#22c55e', stroke: '#15803d', strokeWidth: 1.5
              }
            },
            markup: [{ tagName: 'circle', selector: 'portCircle' }]
          }
        },
        items: portItems
      }
    }, { markup: markup });
  }

  // IO pads (inputs A,B,C and output Z) — rectangles with one port.

  var InputPad = dia.Element.define('logic.InputPad', {
    size: { width: 50, height: 30 },
    attrs: {
      body: {
        x: 0, y: 0, width: 50, height: 30,
        fill: '#dbeafe', stroke: '#1e3a5f', strokeWidth: 1.5, rx: 4, ry: 4
      },
      label: {
        x: 25, y: 15,
        textAnchor: 'middle', textVerticalAnchor: 'middle',
        fontSize: 14, fontWeight: '700', fill: '#1e3a5f',
        fontFamily: 'system-ui, sans-serif',
        pointerEvents: 'none'
      }
    },
    ports: {
      groups: {
        out: {
          position: { name: 'absolute' },
          attrs: {
            portCircle: {
              r: 4, magnet: true,
              fill: '#22c55e', stroke: '#15803d', strokeWidth: 1.5
            }
          },
          markup: [{ tagName: 'circle', selector: 'portCircle' }]
        }
      },
      items: [{ id: 'out', group: 'out', args: { x: 50, y: 15 } }]
    }
  }, {
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'label' }
    ]
  });

  var OutputPad = dia.Element.define('logic.OutputPad', {
    size: { width: 50, height: 30 },
    attrs: {
      body: {
        x: 0, y: 0, width: 50, height: 30,
        fill: '#fef3c7', stroke: '#92400e', strokeWidth: 1.5, rx: 4, ry: 4
      },
      label: {
        x: 25, y: 15,
        textAnchor: 'middle', textVerticalAnchor: 'middle',
        fontSize: 14, fontWeight: '700', fill: '#92400e',
        fontFamily: 'system-ui, sans-serif',
        pointerEvents: 'none'
      }
    },
    ports: {
      groups: {
        in: {
          position: { name: 'absolute' },
          attrs: {
            portCircle: {
              r: 4, magnet: 'passive',
              fill: '#fff', stroke: '#1e3a5f', strokeWidth: 1.5
            }
          },
          markup: [{ tagName: 'circle', selector: 'portCircle' }]
        }
      },
      items: [{ id: 'in1', group: 'in', args: { x: 0, y: 15 } }]
    }
  }, {
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'label' }
    ]
  });

  // ---------------------------------------------------------------------------
  // Per-editor initialization
  // ---------------------------------------------------------------------------

  function initEditor(host) {
    var paperEl = host.querySelector('.circuit-paper');
    var paletteEl = host.querySelector('.circuit-palette');
    var resetBtn = host.querySelector('.circuit-reset');
    if (!paperEl || !paletteEl) return;

    var inputs = (host.dataset.inputs || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    var output = (host.dataset.output || 'Z').trim();

    var graph = new dia.Graph({}, { cellNamespace: shapes });

    var paperWidth = paperEl.clientWidth || 600;
    var paperHeight = 360;

    var paper = new dia.Paper({
      el: paperEl,
      model: graph,
      width: paperWidth,
      height: paperHeight,
      gridSize: 10,
      drawGrid: { name: 'dot', args: { color: '#d1d5db' } },
      background: { color: '#fafafa' },
      cellViewNamespace: shapes,
      defaultLink: function () {
        return new shapes.standard.Link({
          attrs: {
            line: { stroke: '#1f2937', strokeWidth: 2, targetMarker: null, sourceMarker: null }
          },
          router: { name: 'manhattan', args: { padding: 8 } },
          connector: { name: 'rounded' }
        });
      },
      linkPinning: false,
      snapLinks: { radius: 16 },
      markAvailable: true,
      validateConnection: function (cellViewS, magnetS, cellViewT, magnetT, end, linkView) {
        if (cellViewS === cellViewT) return false;
        if (!magnetS || !magnetT) return false;
        var sourceGroup = magnetS.getAttribute('port-group');
        var targetGroup = magnetT.getAttribute('port-group');
        return sourceGroup === 'out' && targetGroup === 'in';
      },
      validateMagnet: function (cellView, magnet) {
        return magnet.getAttribute('port-group') === 'out';
      }
    });

    function placePads() {
      var pad = 30;
      var spacingY = inputs.length > 1
        ? Math.min(90, (paperHeight - 2 * pad) / (inputs.length - 1))
        : 0;
      inputs.forEach(function (name, i) {
        var y = inputs.length > 1
          ? pad + i * spacingY
          : paperHeight / 2 - 15;
        var pad_el = new InputPad({
          position: { x: 16, y: y },
          attrs: { label: { text: name } }
        });
        pad_el.set('logicRole', { kind: 'input', name: name });
        graph.addCell(pad_el);
      });
      var outPad = new OutputPad({
        position: { x: paperWidth - 70, y: paperHeight / 2 - 15 },
        attrs: { label: { text: output } }
      });
      outPad.set('logicRole', { kind: 'output', name: output });
      graph.addCell(outPad);
    }

    placePads();

    // Drag from palette buttons into paper
    Array.prototype.forEach.call(paletteEl.querySelectorAll('.circuit-gate'), function (btn) {
      btn.setAttribute('draggable', 'true');
      btn.addEventListener('dragstart', function (e) {
        e.dataTransfer.setData('text/x-gate', btn.dataset.gate);
        e.dataTransfer.effectAllowed = 'copy';
      });
      // Click also adds the gate (centered) — friendlier on touchpads
      btn.addEventListener('click', function () {
        var GateClass = GateClasses[btn.dataset.gate];
        if (!GateClass) return;
        var g = new GateClass({
          position: { x: paperWidth / 2 - 30, y: paperHeight / 2 - 20 }
        });
        graph.addCell(g);
      });
    });

    paperEl.addEventListener('dragover', function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });
    paperEl.addEventListener('drop', function (e) {
      e.preventDefault();
      var gateName = e.dataTransfer.getData('text/x-gate');
      if (!gateName) return;
      var GateClass = GateClasses[gateName];
      if (!GateClass) return;
      var local = paper.clientToLocalPoint(e.clientX, e.clientY);
      var g = new GateClass({
        position: { x: local.x - 30, y: local.y - 20 }
      });
      graph.addCell(g);
    });

    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        graph.clear();
        placePads();
      });
    }

    // Delete selected link/element on Backspace/Delete when paper has focus.
    var selected = null;
    paper.on('cell:pointerdown', function (cellView) { selected = cellView.model; });
    paper.on('blank:pointerdown', function () { selected = null; });
    paperEl.tabIndex = 0;
    paperEl.addEventListener('keydown', function (e) {
      if ((e.key === 'Backspace' || e.key === 'Delete') && selected) {
        // Don't delete pre-placed pads
        var role = selected.get && selected.get('logicRole');
        if (role) return;
        selected.remove();
        selected = null;
        e.preventDefault();
      }
    });
  }

  function initAll() {
    Array.prototype.forEach.call(document.querySelectorAll('.circuit-editor'), initEditor);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
