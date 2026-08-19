# Weight Manager (权重管理器)

A C4D/Maya-style **weight painting panel** add-on for Blender.

- **Vertex group list** with lock icons, per-row average-weight bar, joint filter, and influence-range highlight (like C4D's Joints list).
- **Absolute / Add / Subtract / Smooth** weight sliders (drag, or hover + `Ctrl+wheel`).
- **Mirror** weights +X→-X / +Y→-Y / +Z→-Z, **Copy/Paste** per-vertex weights, **Normalize** (respects locked groups).
- **Vertex weight table**: select a vertex, see every bone's weight as editable sliders (like Maya's Component Editor).
- **Select-by-weight** (=0 / >0 / <1 / =1 / ≈threshold).
- **Edge-loop picking** in Weight Paint mode: click to select an edge, `Alt+click` loop, `Ctrl+click` shortest path (chains on consecutive clicks), `Shift+click` toggle.
- **Select filled faces' boundary loop** directly in Weight Paint mode (edit-mode "Select Boundary Loop" behavior).
- **Weight HUD**: live value under the cursor.
- One-click **Fill Select** integration (`Shift+Q`, requires the Fill Select add-on).

Works in Blender **4.2+** (verified on 4.2 / 4.5 / 5.0 / 5.1).

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