# Weight Manager (权重管理器)

A C4D/Maya-style **weight painting panel** for Blender — precise, brush-free weight editing in a side panel.

## Features

- **Vertex group list (Joints-style)** — real list (not a dropdown), per-row lock icon + average-weight bar for selected vertices, joint filter (show only groups affecting the selection), and live **influence-range highlight** in the viewport.
- **Weight sliders — Absolute / Add / Subtract / Smooth** — drag to set / accumulate / smooth the active group's weight on selected vertices. Hover the value and `Ctrl+Wheel` for fine steps. Adjustable strength and smooth radius.
- **Mirror & Copy/Paste** — directional mirror (**+X→-X / +Y→-Y / +Z→-Z**, whole group, no pre-selection needed) and per-vertex copy/paste in selection order.
- **Normalize** — rescale all groups on selected vertices to sum to 1; 🔒 locked groups stay untouched.
- **Vertex weight table** — select a vertex, edit **every bone's** weight as a slider (locked groups read-only; sorted by weight, zeros at the bottom — drag a 0 up to add a bone).
- **Select by weight** — =0 / >0 / <1 / =1 / ≈threshold.
- **Weight HUD** — live `bone: value` readout under the cursor.
- **Edge-loop picking in Weight Paint mode** — click to select an edge, **`Alt+click`** a loop, **`Ctrl+click`** a shortest path (chains on consecutive clicks), **`Shift+click`** to toggle — just like Edit Mode, without leaving Weight Paint. Also **selects a filled face region's boundary loop** directly (Edit-Mode "Select Boundary Loop" behavior).
- **Fill Select integration** — fill faces between two loops (`Shift+Q`) right from the panel, in both Edit and Weight Paint modes (requires the **Fill Select** add-on).

## Installation

- **From the platform (recommended):** *Edit → Preferences → Add-ons → search "Weight Manager" → enable it.*
- **Manual (zip):** *Edit → Preferences → Add-ons → "Install from Disk…" → pick `weight_manager.zip` → enable it.*
- The panel appears in the **3D Viewport sidebar (N key) → Weight Mgr** tab.

## Quick usage

1. Select a mesh, then pick a vertex group (bone) in the Joints list.
2. Select vertices/faces to affect (Edit Mode or Weight Paint — enable **face/vertex mask** at the panel top in Weight Paint to see wireframe and box-select).
3. In **Auto Weight** pick a mode and drag the slider (or `Ctrl+Wheel` on the value):
   - **Absolute** — set selected vertices to the slider value.
   - **Add / Subtract** — keep accumulating by drag amount (auto resets to 0 after each step, so you can repeat).
   - **Smooth** — average toward the neighborhood (radius 1 = direct neighbors only).
4. Use **Commands** to invert / mirror / copy / paste, **Normalize** to rebalance to total 1 (locked groups kept), **Select by weight** to pick vertices.
5. Want the faces between two loops? Select them as edge loops → **`Shift+Q`** (or the panel's Fill Select button) fills them — same in Edit and Weight Paint modes.

## Shortcuts (edge-loop picking)

| Keys | Action |
|---|---|
| Click | Select edge |
| `Alt` + Click | Select loop |
| `Ctrl` + Click | Shortest path (chains on consecutive clicks) |
| `Shift` + Click | Toggle add/remove |
| `Shift+Q` | Fill Select (with Fill Select add-on) |
| RMB / `Esc` | Exit picking mode |

## Compatibility

Works in Blender **4.2+** (verified on 4.2 / 4.5 / 5.0 / 5.1), Edit Mode and Weight Paint Mode. API differences across versions are handled automatically (bmesh deform layer for editing, `lock_weight` compatibility, safe weight reads).

## License

**GNU GPL-3.0-or-later**. See [LICENSE](LICENSE).

Report issues at the [Issues](https://github.com/skulunna-blip/blender-weight-manager/issues) page.

(c) 2026 lunna-sku
