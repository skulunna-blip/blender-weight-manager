# Weight Manager (权重管理器)

对标 **C4D 的 Weight Manager（权重管理器）** 面板，把刷权重从「权重绘制模式+笔刷」变成「面板+拉条」，全部操作集中在 3D 视口右侧侧栏。

## 功能

| 分类 | 功能 | 说明 |
|---|---|---|
| **顶点组列表** | Joints 列表 | 真正的列表控件（非下拉框），逐行显示顶点组（骨骼）+ 锁定图标，点选即切换当前组（对标 C4D 的 Joints 列表）；**每行右侧还有当前组在选中点上的平均权重百分比条**（对标 C4D 的百分比条） |
| | Joint Filter 关节过滤器 | 一键「仅显示影响选中点的关节」（隐藏无关骨骼）+ 按名称搜索骨骼，列表实时过滤（对标 C4D 的 Joint Filter） |
| | 影响范围高亮 | 点选关节（顶点组）→ 视口实时高亮它影响到的顶点（橙色点，权重>0），刷权重前一眼看清这根骨骼盖住了哪些点（对标 C4D 点关节显示影响范围） |
| **权重绘制模式** | 选择遮罩开关 | 权重绘制模式下面板顶部一键开关「面遮罩/点遮罩」（`use_paint_mask`/`use_paint_mask_vertex`），开了才能在权重模式下看见线框、框选/Alt+点选点面（Blender 原生功能，藏得深，面板帮你露出来）。快捷键：Alt+左键 选面、Shift+Alt 加选、B 框选、A 全选 |
| **Auto Weight** | Absolute | 横向大滑条：点哪跳到哪个值、拖动实时把选中顶点权重**设为**条位对应的值（原生滑条，色块填充展示当前百分比） |
| | Add / Subtract | **拖动滑条，或鼠标悬停在滑条数值上按 Ctrl+滚轮**，权重按变动幅度持续叠加/叠减（方向不影响，只看变动了多少，应用后自动归零、可反复叠加）；Strength 控制每次叠加的最大幅度，滚轮是小步进，滚多格累计 |
| | Smooth | 拖动或 Ctrl+滚轮，按变动幅度持续把选中点权重向邻域平均靠拢；**半径**可调（1=只取直接相邻，2/3=影响范围更大、平滑更彻底） |
| | 应用一次（按 Strength） | 不想拖，直接按当前 Strength 应用一次 |
| **Commands** | 反转 | w → 1−w |
| | 镜像 | **+X→-X / +Y→-Y / +Z→-Z**：把当前组在一侧顶点的权重整体镜像到对侧对称顶点（对标 C4D 镜像，不用先选点，一键把半边刷好的权重复制过去） |
| | 复制 / 黏贴 | 复制当前骨骼在选中点上的权重值 → 换选其他点 → 黏贴，按选中顺序一一对应（对标 C4D 的 Copy/Paste；点数和复制的不同时只黏贴前几个并提示） |
| **Normalize 归一化** | 归一化选中点 | 把选中顶点的**所有权重组按比例缩放，使总和 = 1**；列表里**锁定（🔒）的骨骼组权重保持不变**，只调整其余组补足（对标 C4D「锁关节归一化」） |
| **按权重选择** | =0 / >0 / <1 / =1 / ≈阈值 | 对标 C4D 的 Fill Selection |
| **顶点权重表** | 选中点显示所有骨骼权重数字，可改 | 选中顶点 → 上面列表逐点切换 → 下面逐骨骼拖滑条改权重（锁定组只读；按权重降序，0 在最底，把 0 调大 = 给该点加骨骼）；对标 Maya Component Editor / C4D 的精确数值查看 |
| **权重 HUD** | 光标旁实时显示当前骨骼在鼠标所指顶点上的权重值 | 编辑/权重绘制模式开着，鼠标移到网格上即显示 `骨骼名: 数值`；对标 C4D 视口 HUD |
| **边环选择** | 权重绘制模式面板按钮进选边模式 | 权重绘制模式原生没有边选择，点面板「进入选边模式」→ 到视口像编辑模式一样选边：**单击选单条边 · Alt+单击 选整条循环边 · Ctrl+单击 拾取最短路径（Ctrl+Shift 加选路径） · Shift 加选 / 点击已选边取消**（v1.9.11 / v1.9.19 / v1.9.20，完全对标编辑模式键位），编辑/权重模式都能用，选中边/环加粗橙色高亮、**Fill Select 填出的面橙色填充高亮**（v1.9.13，被模型遮挡的不显示，同编辑模式不开透显）；配合 Fill Select 选中两条环 → **Shift+Q** 一键填中间面，和编辑模式操作完全一致 |
| | 选填充面轮廓边 | Fill Select 填充后点「选填充面轮廓边」→ 选中填充区域的外圈轮廓边（对标编辑模式 Select Boundary Loop / `region_to_loop`；权重模式原生没有，纯 Python 复刻），Ctrl+单击 可沿轮廓延伸最短路径（v1.9.21） |
| **顶点组管理** | 新建 / 删除 / 重命名 / 锁定 | 列表里选中即为当前操作组 |
| **联动填充选择** | 一键填充选择 | 集成「Fill Select 填充选择」插件（`mesh.fill_select`），编辑模式和权重绘制模式都能直接用，不用来回切模式；权重绘制模式下 **Shift+Q** 也和编辑模式一样触发填充 |

## 安装

1. 打开 Blender → `Edit` → `Preferences` → `Add-ons`
2. 点右上角 `Install…`，选择 `weight_manager.zip`
3. 勾选启用 **"Mesh: Weight Manager (权重管理器)"**
4. 3D 视口按 `N` 打开右侧侧栏，切到 **Weight Mgr** 标签

## 用法

1. **选物体**（网格），在侧栏顶点组列表里点选一个组（= 骨骼）。**点一下列表里的骨骼，视口会用橙色点高亮它影响到的顶点**（列表上方可关「高亮当前组影响范围」）；骨骼多到看不清？列表上方开「仅显示影响选中点的关节」或搜名字，先选中点再过滤，列表只留下有影响的骨骼
2. **选中要刷的点/面**（编辑模式或权重绘制模式）
   - 权重绘制模式下想看线框/框选点面：先在面板顶部打开「面遮罩」或「点遮罩」（默认关闭，Blender 原生开关）
     - **点遮罩**开启后未选中的顶点会显示为黑色（正常），要先框选/点选顶点（Alt+左键选面、B 框选、A 全选），选中区才显示权重色；嫌黑看不清就用**面遮罩**（未选中面只变暗，仍看得出形状）
     - 要刷左边右边自动跟着动：用 **Blender 自带笔刷镜像**（3D 视口顶部笔刷旁的 X/Y/Z 按钮；插件面板不再提供开关，实测面板开关对实际笔刷无效果）
3. 在 **Auto Weight** 选一个模式：
   - **Absolute**：拖动/点击滑条 → 选中点权重立即变为条位对应的值（点哪跳到哪）
   - **Add / Subtract**：**拖动滑条，或把鼠标悬停在滑条右侧的数值上按 Ctrl+滚轮**，权重跟着变动幅度持续叠加/叠减（注意：Blender 里滚轮微调数字框要按 Ctrl，裸滚轮无效），方向不影响、只看变动了多少，每次应用后条自动归零，可以反复拖/滚继续叠加；不想拖就调好 Strength 点「应用一次」
   - **Smooth**：拖动或 Ctrl+滚轮，越拖/滚越平滑；**半径**默认 1（只取直接相邻），想一次平滑更大范围调到 2/3
4. 用 **Commands** 区做反转；**镜像**（+X→-X / +Y→-Y / +Z→-Z，把当前组一侧顶点的权重整体镜像到对侧，不用先选点）；**复制权重**（当前骨骼在选中点上的值）→ 换选其他点 → **黏贴权重**，按选中顺序一一对应
5. 权重总和不是 1 想归一化：选中点 → **Normalize 归一化** → 总和=1；列表里锁了某些骨骼（🔒）的话，锁住的保持不动、只调其余的
6. 要快速选点：点 `>0` 等按钮按权重选中本组顶点
7. **精确看/改某个顶点的权重**：编辑或权重绘制模式下选中点 → 面板底部「顶点权重表」出现——上面列表选顶点（点哪行切哪点）、下面列表显示**所有骨骼**在该点的权重数字，拖动滑条直接改（**锁定 🔒 的骨骼行只读**；列表按权重降序，0 在最底，把 0 拖大 = 给该点加这根骨骼）。权重绘制模式开着 **权重 HUD** 开关时，鼠标移到网格上光标旁会实时显示当前骨骼在所指顶点的权重值
8. 要选「两条环之间的面」：用面板里的 **填充选择** 按钮（需已装 Fill Select 插件），编辑模式、权重绘制模式都能直接按，不用先切回编辑模式
9. 权重绘制模式下想**按边环选面**：点面板「进入选边模式」→ 到视口**像编辑模式一样选边**：单击选单条边、**Alt+单击 选整条环**、**Shift 加选 / Ctrl 减选**（连续操作，右键/ESC 退出）→ 用同样方式选中第二条环 → **按 Shift+Q** 一键填出两条环之间的面（和编辑模式操作一致；面板「填充选择」按钮同样能用；对标 C4D 在权重模式选环刷权重的流程；注意权重模式 Alt+左键是原生选面键，所以选边要先进面板按钮，不走快捷键，避免冲突）

> 锁定组（🔒）只读，需先解锁再编辑。

## 版本兼容（跨版本可用）

> **设计目标：换 Blender 版本不用改代码。** 本插件在 Blender **4.x / 5.x** 上均可运行，对 API 差异做了 `getattr` / try-except 兜底。

已处理的版本差异：
- **`VertexGroup.lock` vs `lock_weight`**：Blender 4.2 起锁定属性改名 `lock_weight`，代码自动识别（`_vg_locked()`）
- **编辑模式调 `VertexGroup.add()`**：Blender 5.0 禁止，插件统一走 **bmesh deform layer** 直接写底层数据，任何版本编辑模式都能刷权重
- **不在组中的顶点读权重**：Blender 5 抛异常、旧版返回 0，`_weight()` 统一安全读取

**换版本后插件目录跟着走**（每个 Blender 版本独立目录）：
```
C:\Users\hasee\AppData\Roaming\Blender Foundation\Blender\<版本号>\scripts\addons\
```
把 `weight_manager` 文件夹拷到对应版本目录，重开 Blender 勾选启用即可（或重新 Install zip）。

## 文件结构

```
weight_manager/
├── __init__.py       # 插件入口：operator + N 面板 UI + 设置
├── weight_tools.py   # 核心算法（bmesh deform layer，可无头测）
└── README.md
```

## 验证

- **最短路径改 Ctrl 连点延伸 + 快捷键稳定（v1.9.22，用户反馈「最短路径加选的时候不用再按着 shift 吧，我看编辑模式的时候按住 ctrl 最短路径的时候，再次点的时候就是最短路径加选」）**：v1.9.20 时 Ctrl+Shift 才把路径**加进**选择，用户实测编辑模式是**按住 Ctrl 连续点击，路径从上次选中的边一直延伸加长**、不用按 Shift → 改为 Ctrl 单击最短路径**始终加进现有选择**（= 从活动边延伸，连点路径一直加长），Shift 只留给普通选边时加选/减选。验证 15/15 PASS（原 11/11 + 新增 EXTEND_FIRST/CHAIN/AGAIN/BACK 四节模拟连点延伸：第一次单边、第二次延伸保留、第三次继续加长、点回已选边不破坏延伸链）。回归 verify_boundary 7/7 + verify_plugin_alg 全 PASS。需用户在 GUI 实测确认连点延伸手感。
- **权重模式选填充面轮廓边（v1.9.21，用户要求「权重模式下填充面不能像编辑模式一样选择 select boundary loop 来选择填充面的轮廓边」）**：Fill Select 填充后，编辑模式可用「选择边界环」（原生 `mesh.region_to_loop`，5.0 里 select_boundary_loop 已并入它，Select 菜单里、无默认快捷键）选中填充区域轮廓边，权重模式没有 → 纯 Python 复刻 `_boundary_loop_edges`（语义与 region_to_loop 实测一致：**恰好 1 个邻面被选中的边**，含网格边界边、内部共享边不算）+ 面板「选填充面轮廓边」按钮（`weight.select_boundary_loop`，编辑/权重模式都能用）。关键坑：① 权重模式 `bmesh.from_edit_mesh` 实测抛 **ValueError**（"mesh must be in editmode"）不是 RuntimeError，两种都要接，否则权重模式崩；② EDIT 模式 `mesh.polygons.select` 与 bmesh 不同步（update_edit_mesh 后 mesh 层仍全 True）→ 必须从 bmesh 读；③ 编辑模式全选面会连带把所有边选中 → 虚拟全选守卫（面全 True+边有选中=空）只能用于权重模式。无头聚焦验证 7/7 PASS（编辑模式 4 组 CORNER/LEFT2/ALL4/MID 与原生 region_to_loop 输出完全一致 + 权重模式部分面选中→边界边选中面清空 + 全新网格虚拟全选→CANCELLED）；回归 verify_shortest_path 11/11 + verify_plugin_alg 全 PASS。需用户在 GUI 实测确认按钮手感。
- **选边模式最短路径改 Ctrl+单击 + Shift 改 toggle（v1.9.20，用户反馈「编辑模式的最短路径是按住 Ctrl 不是 Ctrl+Shift，权重模式也一样」）**：键位完全对标编辑模式（用户实测确认 Shift 行为；keymap 源码 `blender_default.py` 核对）：**Ctrl+单击 = 最短路径**（`mesh.shortest_path_pick`，从活动边到点击边，替换选择；**Ctrl+Shift = 把路径加进现有选择**），**Alt+单击 = 选环**（`mesh.loop_select`；Alt+Shift = 环 toggle），**Shift+单击 = 加选 / 点击已选边则取消选择**（编辑模式原生 toggle，替代原 Ctrl 减选；编辑模式本来就没有 Ctrl 减选，Ctrl 已被 shortest_path 占用）。`_native_loop_select` 加 `toggle` 参数；最短路径分支支持 `self.add` 加选；`_do_pick` 报告区分「（加选）/（取消选择）」。聚焦验证 11/11 PASS（原最短路径 8/8 + 编辑模式 toggle 减/加 + 普通单选仍替换）。交互手感需用户在 GUI 实测确认。
- **选边模式支持 Ctrl+Shift 最短路径拾取（v1.9.19，用户要求「编辑模式按 Ctrl+Shift 能拾取最短路径，权重模式不行，就按编辑模式的方法来」）**：选边模式（编辑/权重模式）点选一条边后，**Ctrl+Shift+点击**另一条边 → 沿**最短路径**（Dijkstra 边长加权，节点=边、两条边共享顶点即相邻，与原生 shortest_path 默认一致）**替换**当前选择为该路径（含首尾两端边），活动边更新为目标边 → 连续延伸——完全对标编辑模式 shortest_path 拾取。权重模式没有原生实现，纯 Python 复刻（`_shortest_path_edges` + `_pick_shortest_path`）。无头聚焦验证 8/8 PASS（相邻两横→恰两横、跨列→3 边最短、对角→4 边最短、start==end→单边、不连通→空不崩、活动边无锚/有锚/锚==目标）。交互手感需用户在 GUI 实测确认。
- **正交高亮才可见 + Alt+单击循环不过选 + 点空白取消选边（v1.9.18，用户实测反馈「透视能高亮转正交就没了」+「Alt+点击耳朵区域选了一堆边」+「选边模式点空白没反应该取消选中」）**：① **正交高亮消失 = 偏移方向错**——Blender 5.0.1 正交投影里 **view z 增大 = 深度更小 = 靠前**（旧实现按透视「abs 推远」推导，正交下反而把高亮推到表面后面 → 正交几乎不可见）。`_apply_view_bias` 加 `is_ortho` 参数：正交统一 `+off` 拉近 view z（幅值用 `view_distance×ratio` ≈0.14，与透视同级，比 `max|z|×ratio` 的 0.004 稳亮），透视仍 `+=abs(z)*ratio`。**GUI 探针复刻验证（SUB(-off) 只亮 3px vs ADD(+off) 亮 49px），修正后正交真实 overlay 从 1px → 14px、透视稳定 96px**；② **Alt+click 过度选择 = `_loop_cont` 规则太宽**——旧「≥4 顶点」把三角面网格/耳朵环形当成大环跳过去（UV 球原生也会跨三角，但纯三角游戏网格会被整片圈选）。改**保守规则 `!= 4`：遇到非四边形就停**——纯三角环=原生（环=1）、耳朵等含三角区域不再过选；代价是 UV 球环形出现 6/7 边分叉（原生 8/12），是「不过选」和「环完整性」的取舍；③ **背面剔除改用视线方向**——`_selected_edge_coords` 从「边中点→相机」逐个判（正交下相机在网格中心、方向≈恒等，轮廓边全被剔 + 逐边判定不一致）改成**只剔「所有邻面都背对视线」的边**（法线与视线同向 dot>0，那才真是从背面透出来的线），任何一面朝前/侧对（dot≤0，含轮廓/edge-on 边）都保留，同编辑模式；④ **点空白不取消选边**——`_do_pick` 在编辑/权重模式收到射线未命中网格（`target_idx None`）时清空边+面选择并提示「已取消选择（点在空白处）」而不只是报错。回归 verify_plugin_alg（GRID/CUBE/CYL/ICOSPHERE 与原生 0 不一致、UVSPHERE 保守规则分布）、verify_backface、verify_bias、GUI 探针全 PASS。需用户在 GUI 实测确认正交高亮与 Alt 选环手感。
- **（第三轮）fill 面高亮仍不显示**：`_apply_view_bias` 入参统一 `Vector(v)`（详见下）——本会话回归履带含此修复，回归全 PASS。
- 算法单元测试 24/24 通过（含 Smooth 半径 1/2 层影响范围、Normalize 锁定组保持、Joint Filter 的 group_has_influence）
- 端到端测试（真实 addon 环境）73/73 通过（含真实 `PAINT_WEIGHT` 权重绘制模式回归、Smooth 半径、Fill Select 检测、Normalize 含锁定、Joint Filter 过滤逻辑、影响范围高亮数据源与 draw handler 注册）
- 边环选择聚焦验证（v1.9.0）8/8 通过 × Blender 4.2.16 / 5.0.1 / 5.1.0（环生长、射线选环、非编辑/编辑/叠加写入、键位冲突回归守卫、Fill Select 联动填 8 面）
- 双副本防冲突回归（v1.9.1）4/4 通过 × Blender 4.2.16 / 5.0.1（单一注册、传统先→扩展后、扩展先→传统后、注销无残留——修复「同时装成传统 addon 和扩展时，Blender 5 破坏性重注册导致类注册被踩」）
- **draw 写入限制修复（v1.9.2，真正的 `<UNKNOWN>` 根因）**：顶点权重表从「面板 draw 里直接写 Scene 的 CollectionProperty」改为「draw 只读判断 + `bpy.app.timers` 延迟写入」。Blender 的 GUI 禁止在 draw 回调里改 ID 属性（`Writing to ID classes in this context is not allowed`，无头测不到），此前「编辑模式选面 → 新建顶点组」就会触发。回归：GUI 路径探针 10/10 + 权重表聚焦 15/15 × Blender 4.2.16 / 5.0.1 / 5.1.0（含「draw 不写集合、timer 重建、无死循环重调度」，并顺带修复 HUD 射线路径漏删的 `not ok` 变量——BVHTree 化后会让 HUD 永不显示）
- **GUI 渲染路径修复（v1.9.3）**：表格行 `draw_item` 里 `UILayout.prop()` 误传 `precision` 关键字——该参数只存在于属性定义里，`prop()` 不接收（Blender 4.x/5.x 都不接收），表格首次真正渲染出来时报 `TypeError: invalid keyword argument(s) (precision)`。已删除；精度由 `WeightTableRow.weight` 的 `FloatProperty(precision=3)` 提供。这类错误只有真实 GUI 渲染 UIList 才触发，无头 fake-layout 冒烟测不到
- **边环选择「没点到网格」修复（v1.9.4）**：模态操作符从侧栏按钮启动后，`context.region` 不是鼠标所在的 3D 视口，`event.mouse_region_x/y` 与它错配 → 算出的射线整个射空 → 权重绘制模式点「点一下选边环」总提示「没点到网格」。已改为窗口绝对坐标（`event.mouse_x/y`）+ 显式遍历 `context.screen.areas` 找鼠标下的 3D 视口区域算射线（`_view3d_ray_from_mouse`），并叠加主点 ±3px 采样防落空。这类模态区域坑无头测不到，需在 GUI 实测确认。回归：边环聚焦验证 9/9 × Blender 4.2.16 / 5.0.1 / 5.1.0
- **边环选择「没点到网格」再修（v1.9.6）**：删掉 `invoke` 里的快速路径（v1.9.4 假设模态 region 错配加 `_view3d_ray_from_mouse`，用户仍报错）——Blender 5 面板按钮的 invoke 上下文 `region_data` 可能是有效的 3D 视口（按钮上下文就是 3D 视口 WINDOW region），快速路径用按钮位置立即拾取 → 射线指向按钮像素（面板上）射空 → 当场报「没点到网格」，模态永远等不到用户点边。改为**一律进模态**，等用户在视口点边。用户实测确认「可以了」。
- **边环高亮看不清 + 权重模式网格看不清（v1.9.7）**：选中边环原用 LINES 描边，多数显卡线宽被锁 1px → 视口上几乎看不见。改 TRIS 四边形加粗线（视图空间垂直扩开、透视下按深度缩放、常数屏幕像素宽，三层深色衬底 + 橙色 + 浅黄描边），并压过网格（depth NONE）不受遮挡；权重模式网格本身深色看不清，面板加「显示线框」开关（原生 overlay，藏得深）。加粗高亮效果需在 GUI 实测确认。
- **权重模式 Shift+Q 填充（v1.9.8）**：Fill Select 插件的 Shift+Q 只注册在 "Mesh" keymap（编辑模式才激活），权重模式按了没反应。现由 Weight Manager 给 "Weight Paint" keymap 补注册 Shift+Q → `mesh.fill_select`（fill_select 的 poll 本允许 PAINT_WEIGHT），「选两条边环 → Shift+Q 填中间面」在权重模式和编辑模式操作一致；编辑模式仍走 Fill Select 自己的 Shift+Q，不重复注册。keymap item 按键时才解析 operator → 无条件注册（fill_select 未装时惰性无效、装好即生效），与两插件启用顺序无关。
- **镜像改为定向整组 + 删除笔刷镜像开关（v1.9.9，用户实测反馈）**：① Commands 镜像从「轴选择 + 镜像」改成三个定向按钮 **+X→-X / +Y→-Y / +Z→-Z**——把当前组在 + 侧顶点的权重整体镜像到 - 侧对称顶点（新算法 `mirror_weights_side`，KDTree 找对称点，**不用先选点**，对标 C4D 镜像），删掉 `mirror_axis` 设置属性；② 面板「对称（笔刷镜像）」X/Y/Z 开关删除——用户实测该开关点了对实际笔刷无效果（权重绘制模式笔刷镜像由 Blender 原生控制），用 3D 视口顶部笔刷旁的 X/Y/Z 按钮。
- **选边改两级交互 + 高亮去透显（v1.9.11，用户实测反馈）**：① 之前「点一下就直接选整条环」不符合预期——用户要的是和编辑模式一致的**两级选边**：点面板「进入选边模式」→ 在视口**单击选单条边、Alt+单击 选整条循环边、Shift 加选、Ctrl 减选**（连续操作，右键/ESC 退出；编辑模式走原生 `loop_multi_select`，权重模式用 `_edge_loop_from` 复刻）；② 边环高亮之前 depth NONE 透显式压过网格，被模型挡住的线也可见（像开了 X-Ray）——改 depth `LESS_EQUAL` 正常遮挡，被挡住的线不显示，和编辑模式不开透显时一致。
- **高亮闪烁/线框叠加/填面不高亮（v1.9.12，用户实测反馈）**：① **闪烁** = 线贴网格表面深度几乎相等，LESS_EQUAL 下视角一动 z-fighting 时隐时现——加 `gpu.state.polygon_offset_set(1,1)` 尝试消除（**v1.9.13 发现方向反了，见下条**）；② **「显示线框」开着时选中边「白线 + 半透明橙」叠加**——线框开时改画一层纯不透明橙宽线盖住白线，选中边只有高亮；③ **权重模式 Fill Select 填出的面不高亮**——权重模式没有原生选中面高亮（编辑模式 Face Select 的蓝面），新增 `_selected_face_tris` 画半透明蓝面（mesh.loop_triangles 三角化选中面；**非编辑模式 `polygons.select` 默认全 True「全选」虚拟态，全选视为默认不画，只有部分面 True 才画用户选择**）。
- **高亮整个消失（v1.9.13，用户实测反馈）**：v1.9.12 用 `polygon_offset_set(1,1)` **正值把高亮推离相机**（OpenGL polygon_offset 正值加窗口深度）——线被推进网格后面被 `LESS_EQUAL` 剔除，边和面的高亮一起看不见。改负值 `polygon_offset_set(-1,-1)` 拉近相机，稳定顶到网格面前消除闪烁又不破坏「被遮挡不显示」。面高亮同时从蓝改**编辑模式同款橙**（alpha 0.35→0.45 提亮），权重模式选两条环 → Shift+Q 填出的面一眼可见（已无头验证：权重模式 fill → polygons 部分选择 → 三角顶点非空）。
- **高亮仍未显示，回退 polygon offset（v1.9.14，用户实测反馈「之前版本可以，现在高亮没有，但下方提示选中边、填面也能选」）**：v1.9.13 负值 `polygon_offset_set(-1,-1)` 理论上该显示（拉近相机），但用户 GPU 上**仍不显示**——正值/负值两次都翻车，且用户确认 v1.9.11（LESS_EQUAL + 无 offset）高亮能显示。**移除 polygon offset，回到 v1.9.11 确认能显示的路径**（LESS_EQUAL + 无 offset；贴面线可能轻微 z-fighting 闪烁，但保证高亮能显示）。橙色面高亮保留（v1.9.13）。若用户仍看不到，下一步查 overlay 注册/shader 而非 offset。
- **手动视图深度偏移消闪烁（v1.9.15，用户实测反馈「高亮了，但感觉还是那种闪烁的感觉，和编辑模式里的高亮不太一样」+「直接用编辑模式的高亮方案可以不」）**：**编辑模式高亮本身也是「深度偏移」把选中边拉到网格表面之上稳定显示**（Blender 原生 overlay 同原理）。polygon offset 正/负两次翻车后，改**手动 view 深度偏移**：新增 `_apply_view_bias(verts, view_mat, ratio=0.001)`，把每个顶点在视图空间 z 方向拉近 0.1% 深度（view z 增大 = 靠近相机，相机看向 -z），纯线性变换回世界坐标——绕开 glPolygonOffset 的 GPU 兼容差异，任何显卡行为一致；0.1% 深度足够越过 z-buffer 共面精度（消除闪烁），又远小于前方遮挡的深度差（正常遮挡保持，不穿透成 X-Ray）。面填充 TRIS 和边 quad 顶点都应用。数学已无头验证（verify_bias 5/5：顶点数不变/拉近方向正确/偏移量=ratio×深度/遮挡安全/二次应用单调）。需用户在 GUI 实测确认是否达到编辑模式那种稳定不闪的效果；若不理想可调 ratio 或叠加负 offset 双保险。
- **偏移加大 + 不透明实线（v1.9.16，用户实测反馈「转视角和拉远时有没抗锯齿的感觉」+「显示线框时也像虚线不是实线」）**：0.1% 偏移在**转视角**（边缘深度关系随视角重算）和**拉远**（z-buffer 精度随距离下降）时仍不足，边缘像素在深度测试边界「通过/剔除」抖动 → 断线（**像虚线**）。`_apply_view_bias` ratio 0.001→**0.004**（4 倍拉近，仍远小于遮挡深度差不穿透）；边从「深色描边 + 半透明橙」改**单层不透明橙实线**（编辑模式选中边就是不透明实线；半透明边缘会透出下面权重色/网格，加剧边缘抖动）。线框分支本就不透明橙，同样吃到 0.4% 偏移。verify_bias + 回归全 PASS。需用户在 GUI 实测；若仍虚线，下一步 ratio 0.008 或叠加 polygon offset 负值双保险。
- **偏移到 0.8% + fill 后面/边高亮 + 边模式权重编辑修复（v1.9.17，用户实测反馈「还有一点点没编辑模式的高亮效果好，可以直接把编辑模式的数值搬过去吗」+「选中边后填充选择面就不高亮了」+「边模式下设置权重到选中点提示没点到网格，滑条也不能上边的权重」）**：① `_apply_view_bias` ratio 0.004→**0.008**（编辑模式高亮本身就是深度偏移方案，数值再提一档贴近其稳定度）；② **fill 后「啥都没高亮」修复**——fill 后面部分选中时优先画**选中面的轮廓边**（新 `_selected_face_edge_coords`，从选中面反推其所有边，**不背面剔除**——实测从正上方俯视圆柱时侧面法线全背对相机，背面剔除会把 fill 出的轮廓整条剔光），像编辑模式选中面有橙轮廓；`_selected_face_tris` guard 重构（fill 全选 = 面全 True + 边全 False 放行，旧「全 True 一律不画」会误杀）；③ **边模式「设置权重到选中点」/absolute/add 滑条不生效修复**——边环选择 modal 运行时点侧栏按钮被 modal 吃事件当「点边」→ 射线打按钮报「没点到网格」，改为鼠标不在 3D 视口时 `PASS_THROUGH` 放回 UI；权重模式 `selected_vertex_indices` 从只读 `vertices.select`（默认虚拟全 True → 全网格）改为 **面部分选中→面顶点 / 边部分选中→边顶点 / 顶点部分选中→顶点 / 全 True→全网格** 的 fallback，让选边/fill 后的权重编辑精确作用于边/面的顶点。**（第二轮）**「没点到网格」仍报——GUI 探针实测**侧栏 UI region 与 WINDOW region 边界有 1px 重叠**（`region.x+width` 用 `<=` 判断，侧栏按钮距视口边界 3px 内时 ±3px 角落采样会掉进视口 WINDOW → rays 非空 → 射线射空仍报错）：`_view3d_ray_from_mouse` 改**先查 UI/TOOLS 面板区域，点在面板上直接 None**；`_do_pick` 改**主点必须在 3D 视口内，否则 PASS_THROUGH**（不再无条件收集 ±3px 角落）；并**移除 `BLOCKING`**（否则 PASS_THROUGH 事件仍被 modal 吞，按钮收不到点击）。GUI 探针验证：WINDOW 内 HIT / 侧栏 None。verify_bias + verify_fill_highlight + verify_edge_weight（新增，5/5）+ 回归全 PASS。需用户在 GUI 实测确认。
**（第三轮）fill 面高亮仍不显示（用户报「鼠标填充 2 面后还是不亮」）**——GUI 探针 `tmp/probe_gui_fill.py` 复现：**`_selected_face_tris` 返回 tuple 列表，`_apply_view_bias` 里 `view_mat @ tuple` 抛 `TypeError: Matrix multiplication: not supported between 'Matrix' and 'tuple'`，被 `_draw_edge_overlay` 的 try/except 吞 → 面高亮从 v1.9.15 引入手动 bias 起一直静默不显示**。边链路传 `mw @ Vector(c)`（Vector）一直正常，面一直崩没人发现——探针抓出。修复：`_apply_view_bias` 入参统一 `v = Vector(v)` 再乘矩阵（tuple/Vector 都兼容）。探针复验：fill 后状态（2 面部分选中 + 边全清）下面 TRIS + 面轮廓边绘制链全通（face 12 顶点、edge 14 顶点 → thick 42 顶点 → draw OK）。回归全 PASS。需用户在 GUI 实测确认。
- 安装验证 8/8 通过（zip 安装 → 识别 → 启用 → operator/面板注册）

> 影响范围高亮是 GPU 视口覆盖层，无头环境只能验证「数据源正确 + handler 已注册」，**实际点/渲染效果需在 Blender 里打开看一眼**（点一个骨骼 → 橙色点标出它盖住的顶点）。

## 手动安装（不用 zip）

把 `weight_manager` 文件夹拷到对应版本的用户脚本目录，重开 Blender 勾选启用。

```
C:\Users\hasee\AppData\Roaming\Blender Foundation\Blender\5.0\scripts\addons\
```

## 联动：Fill Select 填充选择插件

面板里的「填充选择」按钮需要已安装 [Fill Select](C:/Users/hasee/blender-fill-select) 插件（`mesh.fill_select`，快捷键 Shift+Q）。未安装时按钮置灰并提示。
