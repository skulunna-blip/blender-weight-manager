# Weight Manager · Development Document (English)

> The full journey from v1.0 to v1.8.0, comparison with C4D / Maya, technical
> architecture, and future directions.
> Chinese version: `开发文档.md`. Project root: `C:\Users\hasee\blender-weight-manager`

---

## 1. Overview

**Weight Manager** is a Blender addon that turns weight painting from "Weight Paint mode
+ brush strokes" into "sidebar panel + sliders + numbers", closely modeled on **Cinema
4D's Weight Manager** panel while absorbing the **Maya Component Editor**'s ability to
"read and edit per-point numbers precisely".

- **Form**: a "Weight Mgr" tab in the 3D viewport's right sidebar (N panel)
- **Compatibility**: Blender **4.2+ / 5.x**, every API difference is handled
- **Current version**: v1.8.0 (2026-08-14)
- **Deliverables**: classic addon zip + official extension format
  (`blender_manifest.toml`, publishable to extensions.blender.org)

**Why it exists**: Blender's native weight tools are "brush + color ramp" — you scrub
back and forth with no numeric feedback. C4D's Weight Manager achieves precise control
with "pick a joint in a panel + set a value with a slider". This addon brings that
interaction into Blender, then adds Maya-style per-point numeric tables.

---

## 2. Development history (10 iterations)

Development from v1.0 to v1.8.0 went through **10 rounds**, each driven by "user
feedback → find the gap → rework → headless verification". No GUI testing was possible —
everything relied on background (headless) test scripts plus code self-review.

### v1.0 · Baseline (Round 1)

Core panel features modeled on C4D:

- Vertex Groups (bones) list: a real list widget + lock icon (🔒), click to switch the
  current group
- Auto Weight: a slider that paints the selected vertices in real time
- Commands: Invert / Mirror
- Select by weight (Fill-Selection style)
- Integration with the Fill Select addon: one-click fill selection

> Round 1 also tried a vertical modal "big button" painter (`WeightOT_DragPaint`); the
> UX was bad and it was scrapped entirely.

### v1.1 · Auto Weight four modes (Round 2)

Feedback: "doesn't feel like C4D — C4D has a bar you can drag", plus the requirement
that **direction must not matter, only distance**:

- `auto_weight_mode` enum, four options: **ABSOLUTE / ADD / SUBTRACT / SMOOTH**
  (ABSOLUTE default)
- ABSOLUTE: native wide horizontal slider, jump-to-value (pure set mode)
- ADD/SUBTRACT/SMOOTH: custom modal drag operator `WeightOT_DragAccumulate`, using
  per-tick increments (`dx = mouse_region_x - last_x`), `dist = |dx|/100 * Strength` —
  direction-independent, distance-only accumulation
- Also an "Apply once (by Strength)" button for non-draggers

### v1.2 · Native slider, free wheel support (Round 3)

Question: "does it support wheel-to-add-weight like C4D's bar?" Conclusion: **Blender's
native slider already fine-tunes the value when hovered + wheel** — no code needed. So
the custom modal operator was deleted in favor of a native property
`settings.drag_bar` (`FloatProperty(subtype="FACTOR", min=-1, max=1, update=_on_drag_bar)`):

- `_on_drag_bar` reads the current delta → `dist = |val| * offset_delta` → dispatch by
  mode to offset/smooth
- After applying, `drag_bar` resets to 0 (assigning 0 in the callback exits early — no
  infinite loop) → the bar visually zeroes after every gesture, infinite stacking
- **Big win**: tests upgraded from "replicating the modal algorithm" to "assigning the
  real property and firing the real callback" — far closer to the real code path

### v1.3 · Weight Paint mode overhaul (Round 4)

Question: "can I see the wireframe and use fill select in weight mode, like C4D?" This
round uncovered a **fatal bug present since v1.0**:

- **🔴 In Weight Paint mode, `context.mode` reads `"PAINT_WEIGHT"`, not
  `"WEIGHT_PAINT"`!** Three places (`_require_mesh_edit`, panel `can_edit`,
  `group_new`) had it wrong, so **every operator silently failed in real Weight Paint
  mode and the panel stayed greyed out**. Fixed everywhere + regression test added
- Select-mask toggles: panel exposes Blender native `use_paint_mask` /
  `use_paint_mask_vertex` so you can see the wireframe and box-select in weight mode
- Fill Select dual-mode: Edit mode uses `from_edit_mesh`; other modes read/write a bmesh
  copy — press Shift+Q right in weight paint mode
- **🔴 `hasattr(bpy.ops.mesh, "fill_select")` is always True** (bpy.ops dynamically
  generates attributes for any string) → the panel wrongly assumed the addon was
  installed and called the wrong idname. Switched to `hasattr(bpy.types, "ClassName")`
  plus dual detection (classic `mesh.fill_select` / extension
  `bl_ext.fill_select_between`)

### v1.4.2 · Wheel & mask fixes (Round 5)

Feedback: "wheel does nothing, vertex mask is all black, what are the mask shortcuts?"

- **🔴 Blender fine-tunes number fields with `Ctrl+wheel` — a bare wheel does nothing.**
  The hint went into the panel
- `drag_bar` set `step=10` (float actual increment = step/100 → 0.1 per notch) for a
  better wheel feel
- Mask shortcuts documented: Alt+Left select face, Shift+Alt add, B box select, A all

### v1.4.3 · Step reverted (Round 5 fix)

- **🔴 Lesson: `step` affects BOTH wheel stepping AND drag feel — a bigger step makes
  dragging coarser.** The user immediately reported "not as good as the previous
  version"; reverted to default step=1 (fine drag), wheel keeps Ctrl + small steps

### v1.5.0 · List percentage bar + Smooth radius + Symmetry (Round 6)

Closed the C4D gap in the order "list percentage bar → Smooth radius → real-time
symmetry":

- **List percentage bar**: each row of `WM_UL_VertexGroups.draw_item` shows a small bar
  with "the average weight of the currently selected vertices on this group"
  (`weight_tools.weight_stats`)
- **Smooth radius**: `smooth_weights` gained a `radius` param (BFS along edges for N
  layers, averaging the neighborhood; radius=1 keeps old behavior); panel SMOOTH mode
  exposes radius 1–5
- **Symmetry toggle**: exposes **`context.tool_settings.weight_paint.use_symmetry_x/y/z`**
  (⚠️ not at tool_settings top level — a top-level `use_symmetry_x` doesn't exist) —
  with symmetry on, painting the left side mirrors to the right

### v1.6.0 · Normalize (Round 7)

Request: "add normalize — and C4D lets you lock joints' weights, right?" (locking already
existed; this round wired Normalize to respect it):

- `normalize_weights(obj, indices, vg_locked)`: locked groups keep their weights, the
  rest are rescaled so each vertex sums to 1; skips vertices whose locked weights already
  reach 1 or that have no editable groups
- **🔴 Lesson: Python implicit multi-line string concatenation must be inside
  parentheses!** `bl_description = "line one, "` followed by `"line two"` on the next
  line without parens → whole addon failed to enable (IndentationError). Fixed by
  wrapping in parentheses

### v1.7.0 · Influence highlight + Joint Filter (Round 8)

Request: "click a joint → viewport highlights its influence" + "Joint Filter":

- **Influence highlight**: `SpaceView3D.draw_handler_add` + POST_VIEW +
  `3D_UNIFORM_COLOR` shader + POINTS (7px orange dots) drawn on vertices with
  weight > 1e-4. Cached data source (key=(id(mesh), vg_idx), 0.35s throttle to avoid a
  full-mesh scan every frame; Edit mode reads live bmesh read-only to avoid redraw
  loops)
- **Joint Filter**: `_joint_filter_flags` pure function (only show joints affecting the
  selection + name search), called from the UIList `filter_items`
- **🔴 Probe (Blender 5.0)**: Edit mode has no native "color by vertex group" overlay
  property → a custom GPU overlay is the only way; `gpu.state.point_size_set` still
  works in 5.0

### v1.7.x · Copy/Paste weights (Round 9) + three real bugs

Request: "copy/paste joint weights" (mirror already existed, so that was just
communication):

- `weight.copy` / `weight.paste` + a module-level `_copy_buffer` list
- **🔴 `set_weights` can't be used for paste** (its second argument is a single scalar
  applied to all points) — per-point values must go through
  `_write_all(obj, vg_idx, list(zip(indices[:n], _copy_buffer[:n])))`. The first version
  passed the whole list to set_weights; the background test caught
  `TypeError: BMDeformVert[key] = x: assigned value not a number`
- **Bug A (real crash)**: `_influence_coords`'s Edit-mode branch called `d.get()` where
  `d` is a BMLayerItem (no `.get`) — an AttributeError spamming every frame in real Edit
  mode. Fixed to `v[d].get(vg_idx, 0.0)`. 🔴 The 0.35s cache fooled the probe — you must
  reset the cache key to test the Edit branch
- **Bug B**: the list percentage bar originally shared `settings.ul_weight_preview` —
  **Blender renders button values only after all draw_item calls finish, so the shared
  property was overwritten by the last row → every row showed the same value.**
  VertexGroup can't hold dynamic attributes → switched to `row.split(factor, align=True)`
  self-drawn ratio bars (value computed and split on the spot)
- **Bug C**: `filter_items` sampled selection even in OBJECT mode (stale selection
  produced a stale filtered list) → only sample in EDIT_MESH/PAINT_WEIGHT

### v1.8.0 · Vertex Weight Table + Weight HUD (Round 10, current)

Request: "vertex weight numeric table" (selected points show every bone's weight,
editable) + weight HUD (confirmed via AskUserQuestion: "table first, and HUD — both this
round"):

- **Vertex Weight Table**: two linked UIList widgets — `WM_UL_WeightVerts` (selected
  vertices) + `WM_UL_WeightRows` (**every bone** for the active vertex, descending,
  zeros at the bottom, each row's slider directly editable)
  - **Each row is an independent `WeightTableRow(PropertyGroup)`** (Bug B's lesson:
    independent instances in a CollectionProperty avoid the shared-FloatProperty
    overwrite trap)
  - Write callback `_on_table_weight` → `weight_tools.set_weights` → `_finish_edit`;
    **respects locks** (locked rows greyed/read-only)
  - Refresh strategy: `_table_populating` guard against loops + signature caching
    (`_table_sel_sig`/`_table_active_vert`/`_table_last_groups`) rebuilds only on change;
    **deleting a group forces a rebuild via the group-count signature** to prevent
    `group_index` drift
- **Weight HUD**: POST_PIXEL draw handler, `obj.ray_cast` to find the vertex under the
  cursor + blf text showing `bone name: weight`; **the whole handler is wrapped in
  try/except** so no draw error can crash the viewport
- **🔴 Round-10 self-review caught 4 real bugs (all fixed)**:
  1. `WM_UL_WeightRows.draw_item` wrongly used `data.vertex_groups` — the rows
     template_list is bound to settings, so every row would AttributeError in the GUI.
     Changed to `context.active_object`
  2. The `weight_hud` toggle wasn't in the panel — added
  3. HUD ray two problems: `obj.ray_cast` works in **object-local coordinates** (a world
     ray misses on translated/rotated objects — must invert `matrix_world`); and
     **Blender 5.0's ray_cast returns a 4-tuple** (`result, location, normal, index`),
     not the old docs' 5-tuple — the ValueError was swallowed by try/except so the HUD
     never drew. Confirmed by probe, fixed
  4. Stale table values: external edits to the same vertex left the table showing old
     numbers. Added `_read_vert_all` (read all groups for one vertex in one pass) +
     per-frame consistency check, rebuild only on mismatch

---

## 3. Comparison with C4D

| Capability | C4D Weight Manager | This addon | Notes |
|---|---|---|---|
| Joint (bone) list | Joints list | Vertex groups list (same list widget + lock 🔒) | click = current group |
| Slider-set weight | Auto Weight | Absolute / Add / Subtract / Smooth | ABSOLUTE jump-to-value; add/subtract accumulate by drag distance |
| Lock-joint normalize | yes | Normalize + locked groups preserved | locked read-only, rescale the rest |
| Copy / Paste | yes | copy/paste weights | one-to-one in selection order |
| Mirror / Invert | yes | Commands mirror / invert | X/Y/Z axis |
| Influence visualization | show influence on joint | influence highlight (orange dots) | same data source |
| Viewport HUD | weight HUD | weight HUD (live value at cursor) | |
| Joint Filter | yes | Joint Filter (affecting-selection + name search) | |
| Select by weight | Fill Selection | select by weight (=0/>0/<1/=1/≈range) | |
| Fill selection | Fill Selection (between loops) | integrated Fill Select addon | |
| Symmetric paint | symmetric | weight-brush symmetry toggle (native) | |

**Verdict**: C4D Weight Manager's **core interaction surface is fully replicated**; the
remaining advanced commands (Remap/Blur) are in §6.

## 4. Comparison with Maya

Maya has no single Weight Manager panel; its weight capabilities live in Paint Skin
Weights and the Component Editor:

| Maya capability | Here | Notes |
|---|---|---|
| Component Editor (per-point weight numbers, directly editable) | **Vertex Weight Table** (v1.8.0) | select points → top list switches point, bottom list edits each bone via slider, descending, zeros at bottom |
| Paint Skin Weights brush | Auto Weight four modes + native brush | this addon's "panel + slider" is more precise than brushing; native brush still available for smudging |
| Per-vertex exact numbers | vertex table + weight HUD | read numbers / show-at-cursor |
| Set / Add / Scale tools | Absolute / Add-Subtract / Smooth | clear correspondence |
| Normalize (Maya forces by default) | Normalize + locked groups | |

**Verdict**: Maya's most-celebrated "Component Editor exact weight editing" lands here as
the **Vertex Weight Table**, complementing the C4D-style panel.

---

## 5. Technical architecture

### 5.1 Code layout

```
weight_manager/
├── __init__.py       # entry: bl_info + operators + N-panel + settings + draw handlers
├── weight_tools.py   # core algorithm layer (bmesh deform layer, headless-testable)
└── README.md
```

- **Algorithm layer `weight_tools.py`**: pure logic, no UI. `_read_all`/`_write_all`
  batch read/write the bmesh deform layer (read once, write once — avoids per-vertex
  Python↔C calls; the performance core)
- **UI layer `__init__.py`**: operators + `VIEW3D_PT_WeightManager` panel +
  `WeightManagerSettings` + two GPU draw handlers

### 5.2 Key technical decisions

1. **Always go through the bmesh deform layer**: Blender 5.0 forbids `VertexGroup.add()`
   in Edit mode — all reads/writes go through `bm.verts.layers.deform.verify()`
   (Edit mode: live bm then `update_edit_mesh`; other modes: bmesh copy + `to_mesh`).
   Weight painting works in Edit mode on every version
2. **Native widgets first**: wheel fine-tuning and slider dragging are built-in Blender
   behavior — use native sliders instead of hand-rolled modals wherever possible
3. **CollectionProperty with per-row instances**: multi-row data (the vertex table)
   must give each row its own PropertyGroup — a shared FloatProperty is overwritten by
   the last row (Bug B lesson)
4. **Draw handlers fully wrapped in try/except**: no draw error may crash the viewport
5. **Performance**: influence data is cached + throttled (0.35s) to avoid a full-mesh
   scan every frame

### 5.3 Cross-version compatibility (4.2+ / 5.x)

- `VertexGroup.lock` → renamed `lock_weight` in 4.2; `_vg_locked()` uses getattr
- `VertexGroup.add()` forbidden in Edit mode → unified bmesh deform layer
- `VertexGroup.weight(i)` raises RuntimeError when the vertex isn't in the group →
  `_weight()` returns 0 safely
- 5.0 `ray_cast` 4-tuple vs old docs' 5-tuple → unpack as 4-tuple uniformly

### 5.4 Testing strategy (all headless background)

- **Algorithm unit tests**: `test/test_algorithm.py`, 24/24 pass
- **End-to-end tests**: `test/test_e2e.py`, 73/73 pass (real addon environment, incl.
  real `PAINT_WEIGHT` mode regression)
- **Install verification**: `test/test_install.py`, 8/8 pass (zip install → detect →
  enable → register)
- **Cross-version**: same script PASSes on 4.2.16 / 5.0.1 / 5.1.0
- **Extension verification**: `tmp/verify_extension.py` — after `read_factory_settings`
  clears state, `addon_utils.enable("bl_ext.user_default.weight_manager")` PASSes
- **Limits**: GPU overlay rendering, UIList rendering/dragging, real wheel feel, HUD ray
  picking — these GUI behaviors can't be tested headless. They rely on **code
  self-review** (which has caught 7 real bugs) + user GUI confirmation

---

## 6. Future directions

Remaining gaps, by priority:

1. **Weight import/export**: export weights to JSON/CSV, or copy weights between meshes
   (Maya's copy skin weights / C4D's transfer)
2. **Remap**: C4D Weight Tool's Remap curve — remap weight values through a curve
   (compress/stretch a range around a threshold)
3. **Blur**: C4D's Blur command — set to neighborhood average by a fixed amount (Smooth
   already moves toward the average by drag distance; Blur is "set to average, repeatable")
4. **Face/point-granularity fill selection**: Fill Select currently fills "faces between
   two loops"; extend to "fill inside a loop" (the full C4D Fill Selection shape)
5. **Auto axis detection for mirror**: infer the symmetry axis from the object's bounds
   / selected-points centroid to reduce manual axis picking
6. **Multi-object batch**: apply the same weight operations to several meshes at once
   (common when clothing/accessories are modeled separately)
7. **Edit-mode auto-normalize hint**: when selected vertices' weight sum drifts from 1,
   show a one-click normalize hint in the panel
8. **Publish to extensions.blender.org**: the `store/` package is ready (manifest +
   flat zip + icon/featured images) — submit for review to release publicly

---

## 7. Summary

| Item | Value |
|---|---|
| Version | v1.8.0 |
| Iterations | 10 rounds |
| Algorithm unit tests | 24/24 |
| End-to-end | 73/73 |
| Install verification | 8/8 |
| Cross-version | Blender 4.2.16 / 5.0.1 / 5.1.0 all PASS |
| Extension | official-format enable all PASS |
| Real bugs caught by self-review | 7 (PAINT_WEIGHT in v1.3, A/B/C in round 9, 1/2/3/4 in round 10) |

**One line**: ten rounds of "feedback → rework → headless verify" turned C4D's
"panel + slider" painting experience and Maya's "per-point numbers" precision into a
complete Blender sidebar addon — from v1.0's feature baseline to v1.8.0's Vertex Weight
Table + Weight HUD, the core interaction gaps are all closed.
