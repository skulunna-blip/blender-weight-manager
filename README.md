# Weight Manager (权重管理器)

A C4D/Maya-style **weight painting panel** add-on for Blender — precise, brush-free weight editing in a side panel.

> Turn Blender's weight painting from "paint with a brush" into "set exact numbers with a panel": pick a bone, select vertices, drag a slider. Everything lives in the 3D viewport sidebar.

## Features

- **Vertex group list (Joints-style)** — a real list (not a dropdown), with per-row **lock icon**, **average-weight bar** for the selected vertices, **joint filter** (show only groups affecting the selection), and a live **influence-range highlight** in the viewport.
- **Weight sliders — Absolute / Add / Subtract / Smooth** — drag to set / accumulate / smooth the active group's weight on selected vertices. Hover the value and `Ctrl+Wheel` for fine steps; adjustable **Strength** and **Smooth Radius**.
- **Mirror & Copy/Paste** — directional mirror (**+X→-X / +Y→-Y / +Z→-Z**, whole group, no pre-selection needed) and per-vertex copy/paste in selection order.
- **Normalize** — rescale all groups on selected vertices to sum to 1; 🔒 **locked groups stay untouched**.
- **Vertex weight table** — select a vertex, edit **every bone's** weight as a slider (locked groups read-only; sorted by weight, zeros at the bottom — drag a 0 up to add a bone).
- **Select by weight** — pick vertices where the active group is =0 / >0 / <1 / =1 / ≈threshold.
- **Weight HUD** — live `bone: value` readout under the cursor.
- **Edge-loop picking in Weight Paint mode** — click to select an edge, **`Alt+click`** a loop, **`Ctrl+click`** a shortest path (chains on consecutive clicks), **`Shift+click`** to toggle — just like Edit Mode, without leaving Weight Paint. Also **selects a filled face region's boundary loop** directly.
- **Fill Select integration** — fill faces between two loops (`Shift+Q`) right from the panel, in both Edit and Weight Paint modes (requires the **Fill Select** add-on).

Works in Blender **4.2+** (verified on 4.2 / 4.5 / 5.0 / 5.1), in **Edit Mode** and **Weight Paint Mode**. API differences across versions are handled automatically.

## Quick start

1. Select a mesh, pick a bone in the **Joints** list.
2. Select vertices/faces to affect (Edit Mode, or Weight Paint with the panel's face/vertex mask enabled).
3. In **Auto Weight**, pick a mode and drag the slider — **Absolute** sets the value, **Add/Subtract** accumulates, **Smooth** averages.
4. Use **Commands** for Invert / Mirror / Copy-Paste / Normalize, and **Select by weight** to grab vertices.
5. In Weight Paint, **`Alt+click`** a loop, **`Ctrl+click`** a shortest path, **`Shift+Q`** to fill between loops.

For the full usage guide, shortcuts and behavior notes, see [store/README.md](store/README.md).

## Repository layout

```
├── store/                  # Official extension package (upload this to the platform)
│   ├── blender_manifest.toml   # Extension metadata (id, version, license, support)
│   ├── __init__.py             # Panel + operators + overlay + registration
│   ├── weight_tools.py         # Core algorithms
│   └── README.md / LICENSE
├── weight_manager/         # Legacy add-on version (zip top-level folder)
├── docs/                   # Tutorial & dev docs (Chinese/English)
├── test/                   # Headless verification scripts
└── LICENSE                 # GPL-3.0-or-later
```

## Install / report issues

- **Install:** from the Blender Extensions Platform, or download the release zip and use *Edit → Preferences → Add-ons → "Install from Disk…"*.
- **Report issues:** use the [Issues](https://github.com/skulunna-blip/blender-weight-manager/issues) page.

## License

**GNU GPL-3.0-or-later**. See [LICENSE](LICENSE).

(c) 2026 lunna-sku
