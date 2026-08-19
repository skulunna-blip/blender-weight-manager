# Weight Manager (权重管理器) — 上架文案

以下为上传 extensions.blender.org 时 **Description** 字段的文案,中英双版,按需粘贴。

---

## English Description

**A C4D/Maya-style weight painting panel — precise weight editing without the brush.**

Turn Blender's weight painting workflow into a panel-driven, exact tool. All controls live in a side panel in the 3D viewport:

- **Vertex group list (Joints-style)** — real list, per-row lock icon + average-weight bar on selected vertices, joint filter (show only groups affecting selection), and live influence-range highlight in the viewport.
- **Weight sliders (Absolute / Add / Subtract / Smooth)** — drag to set / accumulate / smooth weights on selected vertices; hover the value and `Ctrl+Wheel` for fine steps; adjustable strength and smooth radius.
- **Mirror & copy/paste** — directional mirror (+X→-X / +Y→-Y / +Z→-Z, whole group, no pre-selection needed), and per-vertex copy/paste in selection order.
- **Normalize** — rescale all groups on selected vertices to sum to 1; 🔒 locked groups stay untouched.
- **Vertex weight table** — select a vertex, edit every bone's weight as a slider (locked groups read-only; sorted by weight, zeros at the bottom).
- **Select by weight** — pick vertices where the active group is =0 / >0 / <1 / =1 / ≈threshold.
- **Weight HUD** — live `bone: value` readout under the cursor.
- **Edge-loop picking in Weight Paint mode** — click to select an edge, `Alt+click` a loop, `Ctrl+click` a shortest path (chained on consecutive clicks), `Shift+click` to toggle — just like Edit Mode, without leaving Weight Paint. Also selects a filled face region's boundary loop directly.
- **Fill Select integration** — fill faces between two loops (`Shift+Q`) right from the panel, in both Edit and Weight Paint modes (requires the Fill Select add-on).

**Works in Blender 4.2+** (verified on 4.2 / 4.5 / 5.0 / 5.1), in Edit Mode and Weight Paint Mode. API differences across versions are handled automatically.

---

## 中文 Description

**C4D/Maya 式权重管理器——不用笔刷,面板精确调权重。**

把权重绘制从「刷笔刷」变成「面板 + 拉条」的精确工具,全部操作集中在 3D 视口右侧侧栏:

- **顶点组列表(Joints 式)** — 真正的列表控件,逐行锁定图标 + 选中点平均权重条、关节过滤器(只显示影响选中点的组)、视口实时高亮影响范围。
- **权重滑条(Absolute / Add / Subtract / Smooth)** — 拖动即设置/叠加/平滑选中顶点权重;悬停数值 `Ctrl+滚轮` 微调;Strength 与平滑半径可调。
- **镜像 & 复制/黏贴** — 定向镜像(+X→-X / +Y→-Y / +Z→-Z,整组镜像、无需预选点)、按选中顺序逐点复制/黏贴。
- **归一化** — 选中顶点所有权重按比例缩放到总和 = 1;🔒 锁定组保持不动。
- **顶点权重表** — 选中顶点 → 逐骨骼滑条改权重(锁定组只读;按权重降序、0 在最底)。
- **按权重选择** — 选中当前组权重 =0 / >0 / <1 / =1 / ≈阈值 的顶点。
- **权重 HUD** — 光标旁实时显示 `骨骼名: 数值`。
- **权重模式选边环** — 单击选边、`Alt+单击` 选环、`Ctrl+单击` 最短路径(连点延伸)、`Shift+单击` 切换——和编辑模式一致,不用切出权重模式;还能直接选中填充区域的轮廓边。
- **Fill Select 联动** — 面板一键 `Shift+Q` 填两条环之间的面,编辑/权重模式都能用(需装 Fill Select 插件)。

**兼容 Blender 4.2+**(已在 4.2 / 4.5 / 5.0 / 5.1 验证),编辑模式与权重绘制模式均可;跨版本 API 差异自动处理。

---

## Release notes (Initial Version / 首次提交)

**English:**
Initial release of Weight Manager — a C4D/Maya-style weight painting panel for precise, brush-free weight editing. See the description for the full feature list.

**中文:**
Weight Manager 首次发布——C4D/Maya 式权重管理器,面板精确调权重,不用笔刷。功能详见描述。
