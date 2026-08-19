# Weight Manager (权重管理器)

A C4D/Maya-style **weight painting panel** for Blender — precise, brush-free weight editing in a side panel.

- **Vertex group list (Joints-style)** — real list (not a dropdown), per-row lock icon + average-weight bar for selected vertices, joint filter (show only groups affecting the selection), and live **influence-range highlight** in the viewport.
- **Weight sliders — Absolute / Add / Subtract / Smooth** — drag to set / accumulate / smooth the active group's weight on selected vertices. Hover the value and `Ctrl+Wheel` for fine steps. Adjustable strength and smooth radius.
- **Mirror & Copy/Paste** — directional mirror (**+X→-X / +Y→-Y / +Z→-Z**, whole group, no pre-selection needed) and per-vertex copy/paste in selection order.
- **Normalize** — rescale all groups on selected vertices to sum to 1; 🔒 locked groups stay untouched.
- **Vertex weight table** — select a vertex, edit **every bone's** weight as a slider (locked groups read-only; sorted by weight, zeros at the bottom — drag a 0 up to add a bone).
- **Select by weight** — =0 / >0 / <1 / =1 / ≈threshold.
- **Weight HUD** — live `bone: value` readout under the cursor.
- **Edge-loop picking in Weight Paint mode** — click to select an edge, **`Alt+click`** a loop, **`Ctrl+click`** a shortest path (chains on consecutive clicks), **`Shift+click`** to toggle — just like Edit Mode, without leaving Weight Paint. Also **selects a filled face region's boundary loop** directly (Edit-Mode "Select Boundary Loop" behavior).
- **Fill Select integration** — fill faces between two loops (`Shift+Q`) right from the panel, in both Edit and Weight Paint modes (requires the **Fill Select** add-on).

Works in Blender **4.2+** (verified on 4.2 / 4.5 / 5.0 / 5.1), in **Edit Mode** and **Weight Paint Mode**.

---

## Installation

- **From the platform (recommended):** *Edit → Preferences → Add-ons → search "Weight Manager" → enable it.*
- **Manual (zip):** *Edit → Preferences → Add-ons → "Install from Disk…" → pick `weight_manager.zip` → enable it.*
- The panel appears in the **3D Viewport sidebar (N key) → Weight Mgr** tab.

---

## Usage

### 1. The Joints list

Pick a vertex group (bone) to work on. Each row shows a **lock icon** and the group's **average weight on the currently selected vertices**. The **joint filter** (top of the list) hides groups that don't affect the selection, so you can spot the bones that move your selection at a glance. The active group's **influence range is highlighted** live in the viewport.

### 2. Weight sliders

Select vertices/faces to affect (in Edit Mode, or in Weight Paint with **face/vertex mask** enabled at the panel top to see the wireframe and box-select). In **Auto Weight** pick a mode and drag the slider (or hover the value and `Ctrl+Wheel` for fine steps):

- **Absolute** — set selected vertices to the slider value.
- **Add / Subtract** — keep accumulating by drag amount (auto resets to 0 after each step, so you can repeat to layer more).
- **Smooth** — average toward the neighborhood (radius 1 = direct neighbors only).

**Strength** scales the applied value; **Smooth Radius** controls how far the neighborhood reaches.

### 3. Commands

- **Invert** — flip the active group's weight on selected vertices (w → 1−w).
- **Mirror** — copy the whole group from the +X to the −X side (or +Y→−Y / +Z→−Z). Direction is chosen with a toggle; **no pre-selection needed** — it mirrors the entire group.
- **Copy / Paste** — per-vertex copy/paste in selection order: select the source vertex, copy, select the target, paste. Both vertices must be in the same mesh.
- **Normalize** — rescale all groups on selected vertices so they sum to 1; **🔒 locked groups stay untouched** (their weight is preserved, the rest are rebalanced around them).
- **Select by weight** — pick vertices where the active group is **=0 / >0 / <1 / =1 / ≈threshold** (threshold in the panel).

### 4. Vertex weight table

Select a vertex, and the table shows **every bone's weight on that vertex**, sorted by weight (zeros at the bottom). Drag any row's slider to change that bone's weight — drag a 0 up to add the bone, drag a value down to remove it. **Locked groups are read-only** in the table.

### 5. Weight HUD

With the HUD on, hovering the 3D viewport in Weight Paint mode shows a live `bone: value` readout under the cursor — instant feedback on which bone affects what.

### 6. Edge-loop picking in Weight Paint mode

The most powerful part: **select edge loops without leaving Weight Paint**.

| Keys | Action |
|---|---|
| Click | Select an edge |
| `Alt` + Click | Select a loop |
| `Ctrl` + Click | Shortest path (chains on consecutive clicks — keep clicking to extend) |
| `Shift` + Click | Toggle add/remove |
| RMB / `Esc` | Exit picking mode |

While picking, the panel also offers **"Select boundary loop"** — one click selects the boundary loop of a filled face region (the same result as Edit-Mode's "Select Boundary Loop" operator).

### 7. Fill Select integration

With the **Fill Select** add-on installed, select two edge loops and press **`Shift+Q`** (or the panel's Fill Select button) to select all faces between them — in both Edit and Weight Paint modes.

---

## Shortcuts (edge-loop picking)

| Keys | Action |
|---|---|
| Click | Select edge |
| `Alt` + Click | Select loop |
| `Ctrl` + Click | Shortest path (chains on consecutive clicks) |
| `Shift` + Click | Toggle add/remove |
| `Shift+Q` | Fill Select (with Fill Select add-on) |
| RMB / `Esc` | Exit picking mode |

---

## Notes

- Only works on the currently **visible/selectable mesh**.
- Weight reads in Weight Paint mode come from the mesh's vertex groups; in Edit Mode they come from the bmesh deform layer — both stay in sync with Blender's own painting.
- Locked groups (`🔒`) are **protected everywhere**: sliders, table, and Normalize skip them.
- The influence-range highlight and HUD are viewport overlays; they disappear when the panel is closed or the mode changes.

---

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
