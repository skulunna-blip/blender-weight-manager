# -*- coding: utf-8 -*-
"""Weight Manager (权重管理器) — 对标 C4D 的权重管理器面板

3D 视口右侧 N 面板 > Weight Mgr：
- 顶点组（骨骼）列表控件（对标 C4D Joints 列表）
- 横向权重条：拖动/点击直接刷权重到选中点
- Auto Weight：Absolute（点/拖设值）+ Add/Subtract/Smooth（拖动或悬停滚轮持续叠加，方向不影响）
- Commands：反转 / 镜像 / 复制黏贴
- 按权重填充选择（=0 >0 <1 =1 区间）
- 顶点权重表：选中点 → 显示所有骨骼的权重数字，可直接拖滑条改（对标 Maya Component Editor）
- 权重 HUD：视口光标旁实时显示当前骨骼在鼠标所指顶点上的权重值
- 边环选择（C4D 式）：面板「进入选边模式」按钮 → 在 3D 视口像编辑模式一样选边（单击选单条边、
  Alt+单击 选整条循环边、Shift 加选 / 点击已选边取消、Ctrl+单击 最短路径；编辑/权重绘制模式均可），
  橙色 overlay 高亮；「选填充面轮廓边」按钮 = 权重模式对标编辑模式「选择边界环」，把 Fill Select
  填出的面的轮廓边选出来；配合「Fill Select 填充选择」插件选中两条环 → 一键填中间面
- 联动「Fill Select 填充选择」插件：选中两条环 → 一键选中中间面 → 拖条刷权重

插件元信息兼容 4.x / 5.x（在 Blender 5.0.1 无头验证）。
"""
import bpy
import bmesh
import math

ADDON_VERSION = (1, 9, 22)

bl_info = {
    "name": "Weight Manager (权重管理器)",
    "author": "Unity→Blender",
    "version": ADDON_VERSION,
    "blender": (4, 0, 0),
    "location": "3D 视口 > N 面板 > Weight Mgr",
    "description": "对标 C4D 权重管理器：Joints 列表、权重条、Auto Weight、按权重选择、顶点组管理",
    "category": "Mesh",
}

from . import weight_tools  # noqa: E402


# ---------------------------------------------------------------- 工具函数

def _require_mesh_edit(context):
    """非 MESH / 非编辑类模式的调用返回 (False, 原因)。"""
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return False, "需要选中一个网格物体"
    if context.mode not in ("EDIT_MESH", "PAINT_WEIGHT"):
        return False, "请进入编辑模式或权重绘制模式"
    return True, ""


def _active_vg(obj):
    return obj.vertex_groups.active if obj.vertex_groups else None


def _vg_locked(vg):
    """锁定标记：Blender 4.2+ 用 lock_weight，旧版用 lock。"""
    return bool(getattr(vg, "lock_weight", False) or getattr(vg, "lock", False))


def _get_indices(context, obj):
    sm = tuple(context.tool_settings.mesh_select_mode)
    return weight_tools.selected_vertex_indices(obj, context.mode, sm)


def _finish_edit(context, obj, msg):
    """编辑模式下把 bmesh 改动同步回 mesh 并触发重绘。"""
    if context.mode == "EDIT_MESH":
        bmesh.update_edit_mesh(obj.data)
    area = context.area
    if area:
        area.tag_redraw()
    if msg:
        context.window_manager.popup_menu(
            lambda s, c: s.label(text=msg), title="权重管理器", icon="INFO")


def _fill_select_op():
    """返回已安装的「Fill Select 填充选择」operator 的 idname；未安装返回 None。

    同时认出两个版本：
    - 传统插件版：`mesh.fill_select`（类名 MESH_OT_fill_select，仓库根目录那份）
    - 官方扩展版：`bl_ext.fill_select_between`（类名 BL_EXT_OT_fill_select_between，
      store 那份，Blender 4.2+ Extensions 系统，operator 命名空间 bl_ext.*）

    注意：**不能用 `hasattr(bpy.ops.mesh, "fill_select")` 判断**——bpy.ops 命名空间
    对任意字符串都会动态生成属性（恒为 True），必须查 bpy.types 上的真实注册类。
    """
    if hasattr(bpy.types, "MESH_OT_fill_select"):
        return "mesh.fill_select"
    if hasattr(bpy.types, "BL_EXT_OT_fill_select_between"):
        return "bl_ext.fill_select_between"
    return None


def _ul_weight_preview(context, obj, vg):
    """列表行内百分比条的数据：当前组在选中顶点上的平均权重（对标 C4D Joints 列表）。"""
    if context.mode not in ("EDIT_MESH", "PAINT_WEIGHT"):
        return 0.0
    indices = _get_indices(context, obj)
    if not indices:
        return 0.0
    stats = weight_tools.weight_stats(obj, indices, vg.index)
    return stats[3] if stats else 0.0


def _joint_filter_flags(obj, sel_indices, name_filter="", influence_only=False, bitflag=1):
    """Joint Filter 关节过滤器：返回顶点组列表的显示标记（1=显示，0=隐藏）。

    name_filter: 按名称子串过滤（不区分大小写）。
    influence_only: 只保留「在 sel_indices 上有权重（>ε）」的组；无选中点时保留全部
                    （避免列表被清空，也符合「不知道要过滤啥就不过滤」的直觉）。
    纯函数，UIList.filter_items 和测试共用。
    """
    flags = [bitflag] * len(obj.vertex_groups)
    name_filter = (name_filter or "").strip().lower()
    for i, vg in enumerate(obj.vertex_groups):
        if name_filter and name_filter not in vg.name.lower():
            flags[i] = 0
            continue
        if influence_only:
            if not sel_indices:
                continue
            if not weight_tools.group_has_influence(obj, vg.index, sel_indices):
                flags[i] = 0
    return flags


# ---------------------------------------------------------------- 影响范围高亮（视口 overlay）

_draw_handle = None       # SpaceView3D.draw_handler_add 返回的句柄
_infl_cache_key = None    # (id(mesh), vg_index)
_infl_cache_coords = []
_infl_cache_ts = 0.0

# 注册防冲突（v1.9.0 修复）：插件同时装成传统 addon + 扩展时两个副本都会 register()。
# Blender 5 对已注册类做『注销先前+重注册』（register_class C 层），会连带注销
# Scene.weight_manager 指向的 RNA 类型 → 属性变坏/消失 → 访问报
# "error setting WeightManagerSettings.<UNKNOWN>"。本副本如检测到同名类已被注册
# （无论谁注册的），整体保持惰性：不注册、不碰 Scene、不加 overlay，避免破坏。
_registered = False       # 本副本是否实际执行了注册（惰性副本保持 False）


def _bpy_type_name(cls):
    """该类注册进 bpy.types 后的名称。Operator 用 bl_idname 推导（WEIGHT_OT_xxx），
    其余（PropertyGroup/UIList/Panel）就是类名。"""
    if issubclass(cls, bpy.types.Operator):
        return cls.bl_idname.replace(".", "_OT_").upper()
    return cls.__name__


def _influence_coords(obj, vg_idx):
    """当前顶点组权重>ε 的顶点坐标列表（视口高亮数据源）。

    带缓存：切换组立即刷新（key 变化），连续编辑权重时最长 ~0.35s 延迟一次
    （避免每帧重扫整个网格）。编辑模式走 live bmesh 只读，其它模式直读 mesh。
    """
    global _infl_cache_key, _infl_cache_coords, _infl_cache_ts
    import time
    key = (id(obj.data), vg_idx)
    now = time.time()
    if key == _infl_cache_key and now - _infl_cache_ts < 0.35:
        return _infl_cache_coords
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
        d = bm.verts.layers.deform.verify()
        # 注意：d 是 BMLayerItem（没有 .get），必须 v[d].get(...) —— 早期版本误写成 d.get(...)
        # 在真实编辑模式会 AttributeError 每帧刷屏，缓存探针会把它掩盖成"正常"。
        coords = [tuple(v.co) for v in bm.verts if v[d].get(vg_idx, 0.0) > 1e-4]
    else:
        vg = obj.vertex_groups[vg_idx]
        coords = [tuple(v.co) for v in obj.data.vertices
                  if weight_tools._weight(vg, v.index) > 1e-4]
    _infl_cache_key = key
    _infl_cache_coords = coords
    _infl_cache_ts = now
    return coords


def _builtin_shader(name):
    """gpu.shader.from_builtin 跨版本兼容：Blender 5.0 移除 2D_/3D_ 前缀
    （3D_UNIFORM_COLOR → UNIFORM_COLOR，2D_UNIFORM_COLOR → UNIFORM_COLOR）。
    5.0 用旧名会抛 ValueError，兜底试新名；4.x 直接成功。"""
    import gpu
    try:
        return gpu.shader.from_builtin(name)
    except ValueError:
        return gpu.shader.from_builtin(name.replace("3D_", "").replace("2D_", ""))


def _draw_influence_overlay():
    """视口 overlay：在编辑/权重绘制模式下高亮当前顶点组影响到的顶点（对标 C4D 点关节显示影响范围）。"""
    context = bpy.context
    if context.region is None or context.region.type != "WINDOW":
        return
    if context.mode not in ("EDIT_MESH", "PAINT_WEIGHT"):
        return
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return
    settings = getattr(context.scene, "weight_manager", None)
    if settings is None or not settings.influence_highlight:
        return
    vg = _active_vg(obj)
    if vg is None:
        return
    region_data = context.region_data
    if region_data is None:
        return
    try:
        coords = _influence_coords(obj, vg.index)
    except Exception:
        return
    if not coords:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    try:
        shader = _builtin_shader("3D_UNIFORM_COLOR")
        batch = batch_for_shader(shader, "POINTS", {"pos": coords})
        gpu.matrix.load_matrix(region_data.view_matrix)
        gpu.matrix.load_projection_matrix(region_data.window_matrix)
        gpu.matrix.multiply_matrix(obj.matrix_world)
        gpu.state.blend_set("ALPHA")
        gpu.state.point_size_set(7.0)
        shader.bind()
        shader.uniform_float("color", (1.0, 0.55, 0.05, 0.9))
        batch.draw(shader)
    except Exception:
        pass
    finally:
        gpu.state.blend_set("NONE")


# ---------------------------------------------------------------- C4D 式边环选择（权重模式补原生没有的边选择）

_edge_handle = None   # 边环高亮 overlay 的 draw handler 句柄
# 边环选择入口只走「面板按钮 → modal」（Alt+点击 与权重模式原生选面键冲突，不能注册快捷键）。
# _keymaps 保留仅为清理旧版本可能残留的键位项，当前不再往里注册。
_keymaps = []         # (keymap, keymap_item) unregister 时移除


def _point_seg_dist(p, a, b):
    """点 p 到线段 a-b 的距离（欧氏，坐标任意）。"""
    ab = b - a
    ls = ab.length_squared
    if ls <= 1e-12:
        return (p - a).length
    t = (p - a).dot(ab) / ls
    t = min(1.0, max(0.0, t))
    return (p - (a + ab * t)).length


def _pick_edge_from_ray(obj, bm, origin, direction):
    """鼠标射线选边 → 返回 (目标边索引, 错误消息或 None)。

    **只拾取目标边，不生长环**——环选择交给 Blender 原生
    `bpy.ops.mesh.loop_multi_select()`（编辑模式 Alt+点击同款算法，v1.9.10 起）。

    origin/direction 是世界坐标——BMesh 是物体本地坐标，必须经 matrix_world
    逆变换（同 HUD 的坑）。

    **不用 obj.ray_cast**：它打在「应用修改器后」的网格上，返回的面索引对应
    修改后的网格；原始 bmesh 面数不同（细分/镜像等修改器），索引会错位甚至
    越界 → 点中网格也报「没点到网格」。改射原始 bmesh 的 BVHTree——要选的
    边环本来就是原始网格的环。
    """
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    try:
        m_inv = obj.matrix_world.inverted()
        o = m_inv @ origin
        d = (m_inv.to_3x3() @ direction).normalized()
    except Exception:
        return None, "射线计算失败"
    try:
        from mathutils.bvhtree import BVHTree
        loc, _n, index, _dist = BVHTree.FromBMesh(bm).ray_cast(o, d)
    except Exception:
        return None, "射线计算失败"
    if loc is None or index < 0 or index >= len(bm.faces):
        return None, None
    face = bm.faces[index]
    best, best_d = None, float("inf")
    for e in face.edges:
        dist = _point_seg_dist(loc, e.verts[0].co, e.verts[1].co)
        if dist < best_d:
            best, best_d = e, dist
    if best is None:
        return None, None
    return best.index, None


def _loop_cont(l, use_start):
    """从环 l 出发求下一环边（BMLoop 三跳，复刻 Blender 原生 loop_select）。

    use_start=True：l.vert == step 顶点，走 prev 链（面内到 step 顶的上一条边，
    跨邻面，再 prev）；use_start=False：l.vert == 对端顶点（边界边只有单朝向），
    走 next 链。跨边必须流形（不是边界）、邻面必须是四边形（`== 4`）。
    返回下一环边（必含 step 顶点）或 None。

    v1.9.18 有意保守规则（勿改回放行三角）：原生 loop_multi_select 在三角/混合面
    上其实会跨（苏珊娜耳朵环=8 条全邻 [3,4] 面、UV 球极点环会跨 [3,3] 经线边），
    但它也会整圈绕环——苏珊娜原生环长可到 26~36 条，正是用户报的「耳朵多选」。
    `!= 4` 在三角处停：纯三角游戏网格 = 原生（环=1），苏珊娜耳朵不跨三角链（比
    原生短，不多选）。代价：UV 球极点环比原生少 2 条（原生跨三角，我们停），
    接受。回归对 SPHERE 的 UV 网格已按此调整。
    """
    a = l.link_loop_prev if use_start else l.link_loop_next
    if a is None:
        return None
    b = a.link_loop_radial_next
    if b is None or b is a:
        return None  # 跨边是边界边（只有 1 个面）→ 环到头
    if len(b.face.verts) != 4:
        return None  # 邻面不是四边形（三角面 / n-gon）→ 环到头
    n = b.link_loop_prev if use_start else b.link_loop_next
    if n is None or n.edge.index == l.edge.index:
        return None
    return n.edge


def _loop_angle_ok(e, v, cand):
    """环在顶点 v 处的转角判定：来向（沿 e 到 v）与去向（沿 cand 离 v）夹角
    必须 < 90° 才继续。立方体侧面 90° 直拐 → 停（与原生一致：cube 每边只选 1）；
    圆柱纬线 30°~72° 顺流 → 过。"""
    arrival = v.co - e.other_vert(v).co
    dep = cand.other_vert(v).co - v.co
    if not arrival.length_squared or not dep.length_squared:
        return True
    return arrival.angle(dep) < math.radians(90)


def _edge_loop_next(bm, e, v):
    """在顶点 v，沿环边 e 求下一环边（Blender 原生 loop_select 纯 Python 复刻）。

    优先取 loop.vert == v 的环走 prev 链；边界边只有单朝向时（无 loop 从 v 出发），
    用对端顶点 w 的 loop 走 next 链。逐边无头验证与 `bpy.ops.mesh.loop_multi_select()`
    完全一致（GRID8x8/CUBE/CYL/SPHERE，v1.9.10）。
    """
    for l in v.link_loops:
        if l.edge.index == e.index:
            c = _loop_cont(l, True)
            if c is not None and v in c.verts and _loop_angle_ok(e, v, c):
                return c
    w = e.other_vert(v)
    for l in w.link_loops:
        if l.edge.index == e.index:
            c = _loop_cont(l, False)
            if c is not None and v in c.verts and _loop_angle_ok(e, v, c):
                return c
    return None


def _edge_loop_from(bm, start_idx):
    """从单条目标边扩展出整条边环（原生 loop_select 算法），返回边索引集合。

    从目标边两端分别沿环走，直到回到已选边或到头。权重绘制模式用它
    （临时 bmesh 上算，不切 EDIT）。
    """
    start_e = bm.edges[start_idx]
    sel = {start_idx}
    for end_v in (start_e.verts[0], start_e.verts[1]):
        e, v = start_e, end_v
        while True:
            n = _edge_loop_next(bm, e, v)
            if n is None or n.index in sel:
                break
            sel.add(n.index)
            e = n
            v = e.other_vert(v)
    return sel


def _shortest_path_edges(bm, start_idx, end_idx):
    """两点间最短路径（Dijkstra, 边长加权），返回边索引列表（含两端）。

    对标编辑模式 shortest_path_pick（Ctrl+Shift+点击 拾取最短路径）：权重绘制
    模式没有原生实现，纯 Python 复刻。节点 = 边，两条边相邻 = 共享一个顶点，
    边的代价 = 边长（欧氏距离，与原生默认一致）；从活动边到目标边的最小代价
    链即「最短路径」。

    点位步的运动其实发生在「顶点」上：本实现直接对**边图**跑 Dijkstra——
    从 start 边扩散到所有共享顶点的边，直到弹出 end 边，沿 prev 回溯得到边
    链（含首尾）。比「顶点路径 + 补首尾边」更直接，且天然含两端边。

    返回边索引列表（起点→终点）；start==end 返回 [start]；不连通返回 []。
    纯 bmesh（读 verts/edges/坐标），无头可测。
    """
    import heapq
    start = bm.edges[start_idx]
    end = bm.edges[end_idx]
    if start_idx == end_idx or start == end:
        return [start_idx]
    # 顶点 → 相邻边 邻接表（共享顶点的边算相邻；代价 = 那条边的长）
    v_edges = [[] for _ in bm.verts]
    edge_len = [0.0] * len(bm.edges)
    for e in bm.edges:
        li = (e.verts[0].co - e.verts[1].co).length
        edge_len[e.index] = li
        v_edges[e.verts[0].index].append(e.index)
        v_edges[e.verts[1].index].append(e.index)
    # Dijkstra 跑在边上
    INF = float("inf")
    dist = [INF] * len(bm.edges)
    prev = [-1] * len(bm.edges)
    start_i = start_idx
    dist[start_i] = 0.0
    pq = [(0.0, start_i)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == end_idx:
            break
        # 遍历 u 两个端点的所有相邻边
        seen_nei = set()
        for v in (bm.edges[u].verts[0], bm.edges[u].verts[1]):
            for nn in v_edges[v.index]:
                if nn == u or nn in seen_nei:
                    continue
                seen_nei.add(nn)
                nd = d + edge_len[nn]
                if nd < dist[nn]:
                    dist[nn] = nd
                    prev[nn] = u
                    heapq.heappush(pq, (nd, nn))
    if dist[end_idx] == INF:
        return []  # 不连通
    path = [end_idx]
    cur = end_idx
    while cur != start_idx:
        p = prev[cur]
        if p < 0:
            return []  # 异常（理论上不会到）
        path.append(p)
        cur = p
    path.reverse()
    return path


def _view3d_ray_from_mouse(context, win_mx, win_my):
    """窗口坐标 (win_mx, win_my) → 鼠标下 3D 视口的世界射线 (origin, direction)。

    模态操作符里 `context.region` 是「当前上下文区域」——从侧栏按钮启动模态时，
    它往往还是按钮所在的侧栏 UI 区域（或不是鼠标所在的视口），`event.mouse_region_x/y`
    是相对那个区域的坐标，用它算出的射线会整个射空（无修改器网格也报「没点到网格」）。
    这里显式遍历 `context.screen.areas`，找鼠标点所在 VIEW_3D 的 WINDOW 区域，
    用该区域自己的 `region.data`（RegionView3D）算射线。win_mx/win_my 是窗口
    绝对坐标（`event.mouse_x/y`），转成区域相对坐标后再投影。

    v1.9.17 第二轮（GUI 探针实测）：侧栏 UI region 与 WINDOW region 边界有 1px
    重叠（UI x=1575 而 WINDOW 右边界 1576），旧版只认 WINDOW、用 `<=` 边界判断，
    点在侧栏按钮上（尤其侧栏折叠/贴边界时）会命中 WINDOW 返回一条射线 → 射空 →
    报「没点到网格」。现在先查 UI/TOOLS 面板区域，点在面板上直接返回 None（= UI
    点击，不是 3D 拾取，让调用方 PASS_THROUGH 把事件放回按钮）。
    """
    from bpy_extras import view3d_utils
    screen = getattr(context, "screen", None)
    if screen is None:
        return None
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        # 先查面板区域（N 侧栏 UI / T 工具架 TOOLS）：点在按钮面板上 = UI 点击，
        # 不是 3D 拾取 → None（PASS_THROUGH）。区域可 1px 重叠，面板优先。
        on_panel = False
        win_reg = None
        for region in area.regions:
            if region.type in {"UI", "TOOLS"}:
                if region.x <= win_mx <= region.x + region.width and \
                        region.y <= win_my <= region.y + region.height:
                    on_panel = True
            elif region.type == "WINDOW" and win_reg is None:
                if region.x <= win_mx <= region.x + region.width and \
                        region.y <= win_my <= region.y + region.height:
                    win_reg = region
        if on_panel:
            return None
        if win_reg is not None:
            rv3d = getattr(win_reg, "data", None)
            if rv3d is None:
                continue
            rx, ry = win_mx - win_reg.x, win_my - win_reg.y
            origin = view3d_utils.region_2d_to_origin_3d(win_reg, rv3d, (rx, ry))
            direction = view3d_utils.region_2d_to_vector_3d(win_reg, rv3d, (rx, ry))
            return origin, direction
    return None


_edge_face_cache_key = None
_edge_face_cache = {}


def _edge_to_faces(mesh):
    """边索引 → 邻接面索引列表（mesh 层）。拓扑不变时缓存复用。

    Blender 5.0 移除了 `MeshEdge.link_faces`（4.x 有）和 `MeshPolygon.edges`，
    只能从 loop 层构建：每个面的 loop 区间里读 loop.edge_index，记入 边→面 映射。
    权重绘制不改拓扑，用 (id(mesh), 顶点数, 边数, 面数) 做缓存 key，改拓扑才重建。
    """
    global _edge_face_cache_key, _edge_face_cache
    key = (id(mesh), len(mesh.vertices), len(mesh.edges), len(mesh.polygons))
    if key != _edge_face_cache_key:
        m = {}
        loops = mesh.loops
        for fi, p in enumerate(mesh.polygons):
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                m.setdefault(loops[li].edge_index, []).append(fi)
        _edge_face_cache = m
        _edge_face_cache_key = key
    return _edge_face_cache


def _selected_edge_coords(obj, view_axis, mw):
    """选中边的线段端点坐标（物体本地坐标），overlay 画线数据源。

    view_axis: 世界坐标视线方向（view_matrix 逆矩阵的 -z 列），朝场景里。
    v1.9.18 照编辑模式的做法：只有「所有邻面都背对视线」（法线与视线同向，
    dot>0）的边才剔除——那是确实从背面透出来的线；任何一面朝前或侧对视线
    （dot≤0，含轮廓/edge-on 边）都保留。旧实现用「边中点 → 相机」方向逐个判，
    正交下相机在网格中心、方向 ≈ 恒等视线方向，轮廓边全被剔掉 + 边的背面判定
    逐边不一致（用户反馈「透视能高亮转正交就没了」）。权重模式网格实心，
    全背向边不画避免「像透显模式」；法线/邻接信息拿不到或无邻接面（孤立边）
    时退化为全画（overlay 绝不能崩视口）。
    """
    mesh = obj.data
    co = mesh.vertices
    rot = mw.to_3x3()  # 局部法线 → 世界
    edge_faces = _edge_to_faces(mesh)
    coords = []
    for e in mesh.edges:
        if not e.select:
            continue
        front = True
        try:
            faces = edge_faces.get(e.index)
            if not faces:
                front = True  # 无邻接面（孤立/开放边）：信息不足，不剔除
            else:
                front = False
                for fi in faces:
                    n = rot @ mesh.polygons[fi].normal
                    n.normalize()
                    if n.dot(view_axis) <= 0.0:
                        front = True  # 有邻面朝前或侧对视线（轮廓边）→ 画
                        break
        except Exception:
            front = True  # 法线/邻接信息拿不到：不剔除
        if not front:
            continue
        coords.append(tuple(co[e.vertices[0]].co))
        coords.append(tuple(co[e.vertices[1]].co))
    return coords


def _selected_face_edge_coords(obj):
    """选中面的所有边（含内部共享边）的线段端点（物体本地坐标），overlay 画线。

    v1.9.17：Fill Select 填面后把边选择全清了（fill_select 只留面选择），
    _selected_edge_coords 读 edges.select 全空 → 填出的面轮廓边消失（用户报「填充
    选择面后啥都没高亮」）。这里从选中面反推其所有边（边界 + 内部共享边），让
    「填出的面的边」像编辑模式选中面一样有橙色轮廓。

    **不背面剔除**（与 _selected_edge_coords 不同）：编辑模式选中面就是画选中面的
    所有边，不分正背面；fill 选的面构成连续区域，全画符合「选中面轮廓」语义。
    实测从正上方俯视圆柱时侧面法线全背对相机，背面剔除会把 fill 出的轮廓整条剔光
    （v1.9.17 无头回归 FACE_EDGE_COORDS FAIL），故这里不剔除。
    """
    mesh = obj.data
    co = mesh.vertices
    edge_faces = _edge_to_faces(mesh)
    sel_faces = {fi for fi, p in enumerate(mesh.polygons) if p.select}
    if not sel_faces:
        return []
    coords = []
    for ei, e in enumerate(mesh.edges):
        faces = edge_faces.get(ei)
        if not faces:
            continue
        if not any(fi in sel_faces for fi in faces):
            continue
        coords.append(tuple(co[e.vertices[0]].co))
        coords.append(tuple(co[e.vertices[1]].co))
    return coords


def _boundary_loop_edges(obj):
    """选中面的边界环（轮廓）边：**恰好 1 个邻面被选中**的边。对标编辑模式
    `mesh.region_to_loop`（5.0 里 select_boundary_loop 已并入它）——实测 5.0.1 语义：
    选中面区域最外圈所有边（**含网格边界边**），内部共享边（2 个邻面都选中）不算。

    🔴 EDIT 模式 `mesh.polygons.select` 与 bmesh 选择**不同步**（实测 update_edit_mesh
    后 mesh 层仍全 True），必须从 `bmesh.from_edit_mesh` 读；权重模式没有 edit bmesh
    （from_edit_mesh 抛 RuntimeError）→ 回退读 mesh 层。

    权重模式 `polygons.select` 默认全 True（「全选」虚拟态），复用 _selected_face_tris
    的 guard 约定：面全 True 且边有选中 = 默认虚拟态/正在选边 → 面无真选 → 空；
    面全 True 且边全 False = Fill Select 清了边只选面（真全选）→ 按全选算
    （边界 = 网格外圈）。返回边索引集合，供 `weight.select_boundary_loop` 用。
    """
    mesh = obj.data
    is_edit = False
    try:
        bm = bmesh.from_edit_mesh(mesh)  # EDIT 模式
        is_edit = True
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        face_sel = [f.select for f in bm.faces]
        edge_sel = [e.select for e in bm.edges]
    except (RuntimeError, ValueError):
        # 5.0.1 权重模式 from_edit_mesh 实测抛 ValueError（"mesh must be in editmode"），
        # 不是文档里常见的 RuntimeError——两种都要接，否则权重模式崩。
        bm = None
        face_sel = [p.select for p in mesh.polygons]
        edge_sel = [e.select for e in mesh.edges]
    if not any(face_sel):
        return set()
    # 权重模式虚拟全选态守卫：面全 True 且边有选中 = 默认虚拟态 → 空。
    # EDIT 模式跳过——全选面会连带把所有边选中（实测），但那是真全选，边界=网格外圈。
    if not is_edit and all(face_sel) and any(edge_sel):
        return set()
    sel_faces = {i for i, s in enumerate(face_sel) if s}
    edge_faces = _edge_to_faces(mesh)
    out = set()
    for ei, faces in edge_faces.items():
        if sum(1 for fi in faces if fi in sel_faces) == 1:
            out.add(ei)
    return out


def _selected_face_tris(obj, mw):
    """选中面的三角顶点坐标（世界坐标），overlay 画半透明蓝面高亮的数据源。

    权重绘制模式没有原生「选中面高亮」（编辑模式 Face Select 的蓝面）——Fill
    Select 填出的面/原生选的面在权重模式下看不出。用 mesh.loop_triangles
    （4.2+ calc_loop_triangles）三角化选中面，供 GPU TRIS 填充。

    **🔴 坑：非编辑模式 `polygons.select` 默认全 True（「全选」虚拟态）**——新网格
    未做过任何选择时所有面都 select=True，会把整网格画成蓝。v1.9.17 guard 用边
    选择辅助区分「默认全选」和「Fill Select 真全选」（见下），任何异常返回空
    （overlay 绝不能崩视口）。
    """
    try:
        mesh = obj.data
        faces = mesh.polygons
        face_sel = [p.select for p in faces]
        # 面无选中 → 不画
        if not any(face_sel):
            return []
        # 🔴 v1.9.17 guard 重构：旧逻辑「all(select) → 默认虚拟态不画」会误杀
        #    Fill Select 全选场景——fill 后 fill_select 清了所有边选择、面可能全
        #    True（真全选），被当「默认全选虚拟态」拦截 → fill 后面填充不画（用户
        #    报「填充选择面后啥都没高亮」）。用边选择辅助区分：
        #    - 面全 True 且边有选中 → 默认虚拟态或正在选边 → 面没真选 → 不画
        #    - 面全 True 且边全 False → Fill Select 清了边只选面 → 真选 → 画
        #    - 面部分 True → 用户真选的面 → 画
        if all(face_sel) and any(e.select for e in mesh.edges):
            return []
        # 缓存守卫：loop_triangles 已算过就用缓存，别在 draw handler 每帧重算
        # （刷权重时几何不变，缓存一直有效；几何变了缓存自动失效会重算）
        if not mesh.loop_triangles:
            mesh.calc_loop_triangles()
        co = mesh.vertices
        out = []
        for t in mesh.loop_triangles:
            if not mesh.polygons[t.polygon_index].select:
                continue
            for i in t.vertices:
                out.append(tuple(mw @ co[i].co))
        return out
    except Exception:
        return []


def _apply_view_bias(verts, view_mat, ratio=0.008, is_ortho=False, ortho_dist=None):
    """把世界坐标顶点沿视图方向拉近 ratio（深度比例），消除贴面 z-fighting 闪烁。

    v1.9.15/1.9.16：polygon offset 正/负两次翻车（v1.9.12 正值推远被剔除消失、
    v1.9.13 负值用户 GPU 仍不显示）→ 改**手动视图深度偏移**：把每个顶点在视图空间
    z 方向拉近 ratio×深度（视图空间 z 越大越靠近相机），返回偏移后的世界坐标顶点。
    v1.9.16 从 0.1% 提到 0.4%——用户实测 0.1% 在**转视角**（边缘深度关系重算）和
    **拉远**（z-buffer 精度随距离下降）时边缘仍抖，0.4% 更稳定越过共面。v1.9.17
    提到 0.8%（编辑模式高亮本身也是深度偏移方案，数值与效果对应），更贴近编辑模式
    稳定度。拉近量仍远小于「前方网格遮挡」的深度差（正常遮挡保持，不像 X-Ray
    穿透）。绕开 glPolygonOffset 的 GPU 兼容差异，纯线性变换，任何显卡行为一致。

    v1.9.17 第三轮：入参统一转 `Vector` 再乘矩阵——`_selected_face_tris` 返回的是
    **tuple 列表**（`out.append(tuple(...))`），`Matrix @ tuple` 直接 TypeError，
    真实 overlay 里被 try/except 吞 → **面高亮从 v1.9.15 起一直静默不显示**（GUI
    探针复现）。边链路传的是 `mw @ Vector(c)`（Vector），所以边一直正常、面一直崩
    没人发现。

    v1.9.18 第四轮（GUI 探针实测正交根因）：**正交偏移方向与幅值都实测修正**。
    正交相机在 view_location（网格中心），顶点 view z≈0（透视下≈-view_distance≈-17）。
    ① 方向：Blender 5.0.1 正交投影里 **view z 增大 = 深度更小 = 靠前**（与透视「拉近 =
    view z 增大」同向）。旧 `wv.z += abs(z)*ratio` 在正交下按 abs 推 → 高亮往表面后拉
    （「透视选好边转正交就没了」）；改成统一 `+=`（不再 abs，正值就是靠前）。实测对比
    SUB(-off) 只亮 3px、ADD(+off) 亮 49px。
    ② 幅值：正交若用 `max|z|*ratio`（网格局部视深 0.5×0.8%≈0.004），相对正交整面
    z-buffer 跨度和曲面在 1~2px 高亮宽度上的深度差太小，MSAA 边缘被表面盖住 →
    探针实测正交只亮 11px（透视 84px）。改用 ortho_dist（=region_data.view_distance
    ≈ 相机距离）乘 ratio，与透视偏量同级（0.008×18≈0.14），亮度一致、稳亮。
    """
    from mathutils import Vector
    iv = view_mat.inverted()
    if is_ortho:
        # 正交：相机在 view_location（网格中心），顶点 view z≈0。v1.9.18 实测
        # Blender 5.0.1 正交投影里 **增大 view z = 深度更小 = 靠前**（与「透视拉近 =
        # view z 增大」同向，方向是相机侧一致，非单纯 z 大小）。旧 `-=`（view z 减
        # 小）反而把高亮推到表面后面 → 正交下高亮几乎不可见（GUI 探针对比：SUB 只亮
        # 3px、ADD 亮 49px）。统一 `+=` 拉近 view z → 靠前，赢 LESS_EQUAL 深度测试。
        # 偏量 = ortho_dist×ratio（用户传 view_distance），没传则退回网格最大视深×
        # ratio。
        if ortho_dist is not None:
            off = ortho_dist * ratio
        else:
            maxz = 0.0
            for v in verts:
                wv = view_mat @ Vector(v)
                if abs(wv.z) > maxz:
                    maxz = abs(wv.z)
            off = maxz * ratio if maxz > 1e-9 else 0.0
        if off <= 1e-9:
            return list(verts)
        out = []
        for v in verts:
            wv = view_mat @ Vector(v)
            wv.z += off
            out.append(iv @ wv)
        return out
    out = []
    for v in verts:
        v = Vector(v)  # tuple（_selected_face_tris）或 Vector 都能乘
        wv = view_mat @ v
        wv.z += abs(wv.z) * ratio   # 透视：z 更接近 0 = 拉近相机（相机看向 -z）
        out.append(iv @ wv)
    return out


def _thick_line_quads(view_mat, win_mat, region_h, coords, pixel_half):
    """把 LINES 线段坐标转成加粗四边形顶点（世界坐标），屏幕空间常数像素宽。

    `line_width_set` 在很多显卡上被锁到 1px，画 LINES 永远细得看不清；改用
    TRIS 四边形：把每条边在视图空间垂直方向扩开 pixel_half 像素（透视下按深度
    缩放），得到保证宽度的粗线。返回四边形三角形顶点列表。
    """
    from mathutils import Vector
    iv = view_mat.inverted()
    is_ortho = abs(win_mat[3][3]) > 1e-6  # 透视投影第 4 行 4 列 = 0，正交 = 1
    f = abs(win_mat[1][1])                # 透视 = cot(fovy/2)；正交 = 2/(top-bottom)
    verts = []
    for i in range(0, len(coords), 2):
        v1 = Vector(coords[i])
        v2 = Vector(coords[i + 1])
        w1 = view_mat @ v1
        w2 = view_mat @ v2
        diff = w2 - w1
        if diff.length < 1e-9:
            continue
        perp = Vector((-diff.y, diff.x, 0.0)).normalized()  # 屏幕空间垂直方向
        if is_ortho:
            half_view = pixel_half * 2.0 / (f * region_h) if f > 1e-9 else pixel_half
        else:
            depth = -w1.z
            if depth < 1e-6:
                depth = -w2.z
            if depth < 1e-6:
                continue  # 边穿过近裁面，透视投影退化
            half_view = pixel_half * depth / (f * region_h * 0.5) if f > 1e-9 else pixel_half
        off = perp * half_view
        q1 = iv @ (w1 + off)
        q2 = iv @ (w2 + off)
        q3 = iv @ (w2 - off)
        q4 = iv @ (w1 - off)
        verts.extend((q1, q2, q3, q1, q3, q4))
    return verts


def _draw_edge_overlay():
    """权重绘制模式下高亮选中的边环（Blender 权重模式没有原生边高亮）。

    用加粗四边形画（摆脱显卡 1px 线宽锁）：**单层不透明橙实线**（v1.9.16 从「深色
    描边 + 半透明橙」改，编辑模式选中边就是不透明实线；颜色沿用 v1.9.10 调暗的橙）。
    深度测试按正常遮挡（LESS_EQUAL），共面 z-fighting 用**手动视图深度偏移**消除
    （v1.9.15~1.9.17 `_apply_view_bias` 拉近 0.8% 深度）：v1.9.12 polygon offset 正值
    推远 → 高亮被剔除消失；v1.9.13 负值用户 GPU 仍不显示；v1.9.14 回退无 offset 恢复
    显示但闪；v1.9.15 手动 bias 0.1% 转视角/拉远仍闪 → v1.9.16 提到 0.4% + 不透明实线，
    边缘稳定完整（MSAA 平滑）→ v1.9.17 提到 0.8%（编辑模式高亮本身就是深度偏移），
    贴近编辑模式观感。绕开 glPolygonOffset，纯线性变换。

    **选中面高亮**（v1.9.12/1.9.13）：权重模式没有原生「选中面高亮」，Fill Select
    填出的面/原生选的面在权重模式下看不出。画半透明橙面（编辑模式选中面同款色系；
    v1.9.13 从蓝改橙 + 提亮），让「选两条环 → Shift+Q 填面」在权重模式下也能看到
    填出的面。数据源 _selected_face_tris 已无头验证：权重模式 fill → polygons 部分
    选择 → 三角顶点非空。

    **线框叠加**（v1.9.12）：面板「显示线框」开着时 Blender 给所有边画白线，选中边
    会「白线 + 半透明橙」叠加——改为线框开时只画一层纯不透明橙宽线盖住白线，选中边
    只有高亮。挂在 POST_VIEW draw handler，整段 try/except 不能崩视口。
    """
    context = bpy.context
    try:
        if context.region is None or context.region.type != "WINDOW":
            return
        if context.mode != "PAINT_WEIGHT":
            return
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return
        settings = getattr(context.scene, "weight_manager", None)
        if settings is None or not settings.edge_loop_highlight:
            return
        region_data = context.region_data
        if region_data is None:
            return
        mw = obj.matrix_world
        # v1.9.18：正交/透视偏移方向不同——正交相机在网格中心（顶点 view z≈0），
        # 增大 view z = 深度变大 = 往表面后拉（高亮被自身表面挡住，透视选好转正交就
        # 没）；透视相反。传 is_ortho 给 _apply_view_bias 反号。背面剔除改用视线
        # 方向（只剔全背向，保留轮廓边，同编辑模式）。
        is_ortho = region_data.view_perspective == "ORTHO"
        import gpu
        from gpu_extras.batch import batch_for_shader
        try:
            from mathutils import Vector
            # 世界视线方向（朝场景里）：view_matrix 逆矩阵的 -z 列
            view_axis = region_data.view_matrix.inverted().to_3x3() @ Vector((0, 0, -1))
            view_axis.normalize()
            shader = _builtin_shader("3D_UNIFORM_COLOR")
            gpu.state.depth_test_set("LESS_EQUAL")  # 正常遮挡，被挡住的线不显示（同编辑模式不开透显）
            gpu.state.blend_set("ALPHA")
            # 🔴 v1.9.12 用 polygon offset 正值（推远）→ 高亮被剔除整个消失；
            #    v1.9.13 改负值（拉近）用户 GPU 仍不显示；v1.9.14 回退无 offset 恢复
            #    显示但共面 z-fighting 闪烁。v1.9.15 改手动视图深度偏移（_apply_view_bias）
            #    拉近 0.1% 深度——既能显示又不闪，且不依赖 GPU 的 polygon offset。
            try:
                # ---- 选中面高亮（半透明橙，编辑模式选中面同款色系）----
                face_verts = _selected_face_tris(obj, mw)
                if face_verts:
                    face_verts = _apply_view_bias(face_verts, region_data.view_matrix,
                                              is_ortho=is_ortho, ortho_dist=region_data.view_distance)
                    fb = batch_for_shader(shader, "TRIS", {"pos": face_verts})
                    gpu.matrix.load_matrix(region_data.view_matrix)
                    gpu.matrix.load_projection_matrix(region_data.window_matrix)
                    shader.bind()
                    shader.uniform_float("color", (0.85, 0.60, 0.28, 0.45))
                    fb.draw(shader)
                # ---- 选中边高亮（背面剔除；线框开时纯橙盖白线）----
                # v1.9.17：fill 后面部分选中 → **追加**选中面的轮廓边（fill 面的边，
                # 不背面剔除，编辑模式选中面同款橙轮廓）——不替换边选择，避免 fill 的
                # 面选择残留掩盖后续选边（用户反馈「fill 后连选中的边也不亮」）。
                # 新选边时 _do_pick 会清掉 fill 的面选择，高亮回到当前选中边。
                mesh = obj.data
                f_n = sum(1 for p in mesh.polygons if p.select)
                nf = len(mesh.polygons)
                coords = _selected_edge_coords(obj, view_axis, mw)
                if 0 < f_n < nf:
                    coords = coords + _selected_face_edge_coords(obj)
                if not coords and f_n == nf and nf > 0:
                    coords = _selected_face_edge_coords(obj)  # fill 全选兜底
                if not coords:
                    return
                world = _apply_view_bias([mw @ Vector(c) for c in coords], region_data.view_matrix,
                                         is_ortho=is_ortho, ortho_dist=region_data.view_distance)
                try:
                    wire = context.space_data.overlay.show_wireframes
                except Exception:
                    wire = False
                if wire:
                    passes = ((2.0, (0.90, 0.62, 0.28, 1.0)),)  # 不透明橙盖住线框白线
                else:
                    # v1.9.17 用户反馈「视角凑近能看到类似锯齿的高亮边」→ 从 v1.9.16
                    # 单层不透明橙改成 **宽软边 + 窄实芯** 两遍：宽层半透明橙（alpha
                    # 0.28，像素边缘柔化过渡，效果同编辑模式 smoothwire 光晕）+ 窄层
                    # 不透明橙（编辑模式同款，主导色）。实芯不透明仍避免「透过线看到
                    # 下面权重色」的抖动，软边只补最外圈 1px 的锯齿。
                    passes = (
                        (3.2, (0.80, 0.55, 0.25, 0.28)),  # 宽软边：半透明柔化锯齿
                        (1.6, (0.80, 0.55, 0.25, 1.0)),   # 窄实芯：编辑模式同款不透明橙
                    )
                for pixel_w, color in passes:
                    verts = _thick_line_quads(region_data.view_matrix, region_data.window_matrix,
                                              context.region.height, world, pixel_w * 0.5)
                    if len(verts) < 3:
                        continue
                    batch = batch_for_shader(shader, "TRIS", {"pos": verts})
                    gpu.matrix.load_matrix(region_data.view_matrix)
                    gpu.matrix.load_projection_matrix(region_data.window_matrix)
                    shader.bind()
                    shader.uniform_float("color", color)
                    batch.draw(shader)
            finally:
                gpu.state.depth_test_set("LESS_EQUAL")
                gpu.state.blend_set("NONE")
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------- 权重 HUD（视口光标权重值）

_hud_handle = None   # 权重 HUD 的 draw handler 句柄（POST_PIXEL，画 2D 文字）
# HUD 射线用的原始网格 BVHTree 缓存：key=(id(mesh), 顶点数, 面数)。
# 不每帧重建 bmesh（开销大），几何没变时复用；权重绘制时网格几何不变，安全。
# 与边环选择同理：obj.ray_cast 打在修改器后的网格上，面索引对应不上原始网格。
_hud_bvh_key = None
_hud_bvh = None


def _hud_mesh_bvh(obj):
    """原始网格（不含修改器）的 BVHTree，带缓存。"""
    global _hud_bvh_key, _hud_bvh
    key = (id(obj.data), len(obj.data.vertices), len(obj.data.polygons))
    if key != _hud_bvh_key:
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            from mathutils.bvhtree import BVHTree
            _hud_bvh = BVHTree.FromBMesh(bm)
        finally:
            bm.free()
        _hud_bvh_key = key
    return _hud_bvh


def _hud_vert_under_cursor(obj, region, region_data, mx, my):
    """鼠标所指顶点的索引（射线打在面上的最近顶点）；射不到网格返回 None。"""
    from bpy_extras import view3d_utils
    try:
        origin = view3d_utils.region_2d_to_origin_3d(region, region_data, (mx, my))
        direction = view3d_utils.region_2d_to_vector_3d(region, region_data, (mx, my))
    except Exception:
        return None
    try:
        # obj.ray_cast 的射线是**物体本地坐标**，而 region_2d_to_* 给的是世界坐标——
        # 物体有位移/旋转/缩放时不过矩阵逆变换，射线会射空（HUD 永不显示）。
        # 注意：Blender 5.0 的 ray_cast 返回 **4 元组** (result, location, normal, index)
        #（早期版本按 5 元组带 distance 解包会 ValueError，被吞掉后 HUD 永不显示）。
        # 且不能用 obj.ray_cast：修改器后网格的面索引对应不上原始网格，改射原始 BVHTree。
        m_inv = obj.matrix_world.inverted()
        o = m_inv @ origin
        d = (m_inv.to_3x3() @ direction).normalized()
        loc, _n, index, _dist = _hud_mesh_bvh(obj).ray_cast(o, d)
    except Exception:
        return None
    # BVHTree.ray_cast 射空返回 index=-1（旧 obj.ray_cast 才有 (ok, ...) 元组，
    # 改成 BVHTree 后不再有 ok 变量——漏删会 NameError，HUD 永不开）
    if index < 0 or index >= len(obj.data.polygons):
        return None
    face = obj.data.polygons[index]
    co = obj.data.vertices
    best, best_d = -1, float("inf")
    for vi in face.vertices:
        d = (co[vi].co - loc).length_squared
        if d < best_d:
            best, best_d = vi, d
    return best


def _hud_draw_text(mx, my, text):
    """在鼠标旁画一行带深色底的小字（POST_PIXEL，像素坐标，原点在区域左上）。"""
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
    font_id = 0
    blf.size(font_id, 15, 72)
    w, h = blf.dimensions(font_id, text)
    x, y = mx + 16, my + 12
    pad = 4
    quad = (
        (x - pad, y - pad), (x + w + pad, y - pad),
        (x + w + pad, y + h + pad), (x - pad, y + h + pad),
    )
    gpu.state.blend_set("ALPHA")
    try:
        shader = _builtin_shader("2D_UNIFORM_COLOR")
        batch = batch_for_shader(shader, "TRI_FAN", {"pos": quad})
        shader.bind()
        shader.uniform_float("color", (0.0, 0.0, 0.0, 0.6))
        batch.draw(shader)
    finally:
        gpu.state.blend_set("NONE")
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    blf.draw(font_id, text)


def _draw_weight_hud():
    """视口 HUD：光标旁显示当前骨骼在鼠标所指顶点的权重值（对标 C4D 权重 HUD）。

    挂在 POST_PIXEL draw handler 上。整段 try/except——draw handler 任何异常都不能崩掉视口。
    """
    context = bpy.context
    try:
        if context.region is None or context.region.type != "WINDOW":
            return
        if context.mode not in ("EDIT_MESH", "PAINT_WEIGHT"):
            return
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return
        settings = getattr(context.scene, "weight_manager", None)
        if settings is None or not settings.weight_hud:
            return
        vg = _active_vg(obj)
        if vg is None:
            return
        region = context.region
        region_data = context.region_data
        if region_data is None:
            return
        mx = int(getattr(context, "mouse_region_x", -1000))
        my = int(getattr(context, "mouse_region_y", -1000))
        if mx < 0 or my < 0:
            return
        vert = _hud_vert_under_cursor(obj, region, region_data, mx, my)
        if vert is None:
            return
        w = weight_tools._read_all(obj, vg.index, [vert])[0]
        _hud_draw_text(mx, my, f"{vg.name}: {w:.3f}")
    except Exception:
        pass


# ---------------------------------------------------------------- 顶点权重表（选中点 → 所有骨骼权重数字，可编辑）

_table_populating = False   # populate 期间置 True：程序设值不触发写入回调
_table_sel_sig = None       # 缓存：上次的选中点 tuple
_table_active_vert = None   # 缓存：上次的激活顶点索引
_table_last_groups = -1     # 缓存：上次的顶点组数量（删除组会错位 group_index，必须重建）
_table_dirty = False        # 有待执行的延迟重建（draw 回调禁止写 ID 属性，延迟到 timer）
_table_waiting = None       # timer 待执行时捕获的 (context, obj, settings)——timer 里不用
                            # bpy.context（那个状态不可靠），直接用捕获的引用


def _on_table_weight(self, context):
    """顶点权重表某行权重滑块的回调：把值写入该行骨骼在此顶点上的权重。

    self = 行 item（有自己的 group_index + weight），每行独立——不存在共享属性被
    最后一行覆盖的问题（Bug B 的教训）。
    """
    global _table_populating
    if _table_populating:
        return
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return
    settings = getattr(context.scene, "weight_manager", None)
    if settings is None:
        return
    verts = settings.vert_table_verts
    if not verts:
        return
    idx = settings.vert_table_index
    if idx < 0 or idx >= len(verts):
        return
    vert = verts[idx].vert_index
    if vert < 0 or vert >= len(obj.data.vertices):
        return
    gi = self.group_index
    if gi < 0 or gi >= len(obj.vertex_groups):
        return
    if _vg_locked(obj.vertex_groups[gi]):
        return
    weight_tools.set_weights(obj, [vert], gi, self.weight)
    _finish_edit(context, obj, None)


def _read_vert_all(obj, vert):
    """读一个顶点在**所有**顶点组上的权重（一次读取，跨模式）。"""
    n = len(obj.vertex_groups)
    if n == 0:
        return []
    if obj.mode == "EDIT":
        bm, d = weight_tools._get_bm(obj)
        data = bm.verts[vert][d]
        return [data.get(i, 0.0) for i in range(n)]
    return [weight_tools._weight(vg, vert) for vg in obj.vertex_groups]


def _sync_weight_table(context, obj, settings):
    """面板 draw 调用：只读判断权重表是否需要重建；需要时把写入延迟到 timer。

    **🔴 draw 回调禁止修改 ID 属性**——直接对 settings 的 CollectionProperty
    clear()/add() 会报 "Writing to ID classes in this context is not allowed"
    （Blender GUI 才触发，无头测不到）。所以 draw 里只比较签名，真正清空/重建
    CollectionProperty 交给 `_table_write_timer`（非 draw 上下文）执行。

    只在「选中点变化 / 激活顶点变化 / 顶点组数量变化 / 显示值与实际值不一致」时
    重建——滑块拖动期间集合不重建，输入不被打断；也避免 写入→重绘→重建→写入
    死循环（拖动时行值已被 UI 设为新值 == mesh 值，一致性检查不会误触发）。
    """
    global _table_sel_sig, _table_last_groups
    indices = _get_indices(context, obj)
    sig = tuple(indices)
    sel_changed = sig != _table_sel_sig
    groups_changed = len(obj.vertex_groups) != _table_last_groups

    # 无选中顶点：仅当选中/组数变化时清空行表
    if not settings.vert_table_verts:
        if sel_changed or groups_changed:
            _schedule_table_write(context, obj, settings)
        return

    idx = settings.vert_table_index
    if idx >= len(settings.vert_table_verts):
        idx = 0
    vert = settings.vert_table_verts[idx].vert_index
    if vert < 0 or vert >= len(obj.data.vertices):
        return

    needs_rebuild = sel_changed or groups_changed or vert != _table_active_vert
    if not needs_rebuild:
        # 用顶部 Auto Weight / 其它操作改了同一顶点的权重时，表格值会过期——核对一次
        #（O(组数) 单顶点读取，很便宜），不一致才重建。group_index 越界本身也算过期
        #（正常不会出现，防御而已），重建即校正。
        actual = _read_vert_all(obj, vert)
        if any(r.group_index < 0 or r.group_index >= len(actual)
               for r in settings.vert_table_rows):
            needs_rebuild = True
        elif any(abs(r.weight - actual[r.group_index]) > 1e-5
                 for r in settings.vert_table_rows):
            needs_rebuild = True

    if needs_rebuild:
        _schedule_table_write(context, obj, settings)


def _schedule_table_write(context, obj, settings):
    """把权重表重建推迟到非 draw 上下文（bpy.app.timers 下一个空闲时刻）。

    draw 回调里直接写 Scene 的 CollectionProperty 会报 "Writing to ID classes
    in this context is not allowed"。定时器回调不处于 draw 上下文，可以安全写。
    """
    global _table_dirty, _table_waiting
    if _table_dirty:
        return
    _table_dirty = True
    _table_waiting = (context, obj, settings)
    try:
        bpy.app.timers.register(_table_write_timer, first_interval=0.0)
    except RuntimeError:
        # 定时器不可用（极端情况）：直接执行
        _table_dirty = False
        _table_waiting = None
        _table_write_now(context, obj, settings)


def _table_write_timer():
    """一次性 timer：真正重建权重表（写 Scene 的 CollectionProperty）。"""
    global _table_dirty, _table_waiting
    _table_dirty = False
    waiting = _table_waiting
    _table_waiting = None
    _table_write_now(*waiting)
    return None   # 不重复，一次性


def _table_write_now(context, obj, settings):
    """重建顶点权重表两份列表（选中顶点 + 激活顶点的所有骨骼行）。

    只读签名判断在 `_sync_weight_table`（draw）里做；这里只执行写入。
    参数由 `_sync_weight_table` 捕获传进来，timer 里不依赖 bpy.context 的状态。
    """
    global _table_populating, _table_sel_sig, _table_active_vert, _table_last_groups
    if obj is None or obj.type != "MESH":
        return
    if settings is None:
        return
    indices = _get_indices(context, obj)
    sig = tuple(indices)
    _table_populating = True
    try:
        _table_sel_sig = sig
        settings.vert_table_verts.clear()
        for vi in indices:
            settings.vert_table_verts.add().vert_index = vi
        if settings.vert_table_index >= len(settings.vert_table_verts):
            settings.vert_table_index = 0
        _table_last_groups = len(obj.vertex_groups)
        if not settings.vert_table_verts:
            settings.vert_table_rows.clear()
            _table_active_vert = None
            return
        idx = settings.vert_table_index
        if idx >= len(settings.vert_table_verts):
            idx = 0
        vert = settings.vert_table_verts[idx].vert_index
        if vert < 0 or vert >= len(obj.data.vertices):
            settings.vert_table_rows.clear()
            _table_active_vert = None
            return
        _table_active_vert = vert
        settings.vert_table_rows.clear()
        rows = [(g.index, weight_tools._read_all(obj, g.index, [vert])[0])
                for g in obj.vertex_groups]
        rows.sort(key=lambda r: -r[1])   # 权重降序，0 在最底（把 0 调大 = 给顶点加骨骼）
        settings.vert_table_row_index = 0   # 重建后 active 行归位，避免越界
        for gi, w in rows:
            settings.vert_table_rows.add().group_index = gi
            settings.vert_table_rows[-1].weight = w
    finally:
        _table_populating = False


class WeightTableVert(bpy.types.PropertyGroup):
    """顶点权重表：一行 = 一个选中顶点。"""
    vert_index: bpy.props.IntProperty(name="顶点索引", default=0)


class WeightTableRow(bpy.types.PropertyGroup):
    """顶点权重表：一行 = 激活顶点的一根骨骼 + 它的权重（每行独立可编辑）。"""
    group_index: bpy.props.IntProperty(name="骨骼索引", default=-1)
    weight: bpy.props.FloatProperty(
        name="权重", default=0.0, min=0.0, max=1.0,
        precision=3, subtype="FACTOR", update=_on_table_weight,
        description="该骨骼在此顶点上的权重（拖动滑块实时写入）",
    )


# ---------------------------------------------------------------- 设置

def _on_weight_value(self, context):
    """权重值滑块拖动时的实时回调：直接把选中顶点权重设为滑块值（C4D 式拉条刷权重）。"""
    ok, _ = _require_mesh_edit(context)
    if not ok:
        return
    obj = context.active_object
    vg = _active_vg(obj)
    if vg is None or _vg_locked(vg):
        return
    indices = _get_indices(context, obj)
    if not indices:
        return
    weight_tools.set_weights(obj, indices, vg.index, self.weight_value)
    _finish_edit(context, obj, None)


def _on_drag_bar(self, context):
    """C4D 式拖动叠加条：原生滑条，拖动 or 悬停滚轮都会触发（Blender 滑条原生支持滚轮微调）。
    每次变动量按「幅度」叠加/叠减/平滑（方向不影响，只看变动了多少），应用后自动归零等下一次。"""
    val = self.drag_bar
    if val == 0.0:
        return
    ok, _ = _require_mesh_edit(context)
    if not ok:
        self.drag_bar = 0.0
        return
    obj = context.active_object
    vg = _active_vg(obj)
    if vg is None or _vg_locked(vg):
        self.drag_bar = 0.0
        return
    indices = _get_indices(context, obj)
    if not indices:
        self.drag_bar = 0.0
        return
    dist = abs(val) * self.offset_delta
    mode = self.auto_weight_mode
    if mode == "ADD":
        weight_tools.offset_weights(obj, indices, vg.index, dist)
    elif mode == "SUBTRACT":
        weight_tools.offset_weights(obj, indices, vg.index, -dist)
    elif mode == "SMOOTH":
        weight_tools.smooth_weights(obj, indices, vg.index, iterations=1,
                                    factor=min(1.0, dist), radius=self.smooth_radius)
    _finish_edit(context, obj, None)
    self.drag_bar = 0.0


class WeightManagerSettings(bpy.types.PropertyGroup):
    weight_value: bpy.props.FloatProperty(
        name="权重值", default=1.0, min=0.0, max=1.0,
        precision=3, update=_on_weight_value,
        description="拖动滑块实时把选中顶点的权重设为该值（C4D 式拉条刷权重）",
    )
    offset_delta: bpy.props.FloatProperty(
        name="增减量", default=0.1, min=-1.0, max=1.0,
        precision=3,
    )
    select_threshold: bpy.props.FloatProperty(
        name="阈值", default=0.5, min=0.0, max=1.0, precision=3,
    )
    rename_to: bpy.props.StringProperty(name="新名称", default="", maxlen=63)
    auto_weight_mode: bpy.props.EnumProperty(
        name="模式",
        items=[
            ("ABSOLUTE", "Absolute", "点哪跳到哪 / 拖动条直接把选中点权重设为对应值"),
            ("ADD", "Add", "按住拖动条持续叠加：拖动距离越长加得越多，方向不影响"),
            ("SUBTRACT", "Subtract", "按住拖动条持续叠减：拖动距离越长减得越多，方向不影响"),
            ("SMOOTH", "Smooth", "按住拖动条持续平滑：拖动距离越长越平滑"),
        ],
        default="ABSOLUTE",
        description="对标 C4D Weight Manager 的 Auto Weight 模式",
    )
    drag_bar: bpy.props.FloatProperty(
        name="拖动叠加条", default=0.0, min=-1.0, max=1.0,
        subtype="FACTOR", precision=3, update=_on_drag_bar,
        description="Add/Subtract/Smooth 模式的拖动叠加条：拖动滑条（默认 step，手感精细），"
                     "或鼠标悬停在滑条数值上按 Ctrl+滚轮微调（Blender 原生小步进）。按变动幅度"
                     "叠加/叠减/平滑（方向不影响，只看幅度大小），应用后自动归零，可以持续叠加",
    )
    smooth_radius: bpy.props.IntProperty(
        name="平滑半径", default=1, min=1, max=5,
        description="Smooth 的邻域扩展层数（对标 C4D Smooth 的半径）：1 = 只取直接相邻顶点（默认），"
                     "2/3 = 沿边向外扩展更多层，影响范围更大、平滑更彻底",
    )
    influence_highlight: bpy.props.BoolProperty(
        name="高亮当前组影响范围", default=True,
        description="编辑/权重绘制模式下，视口高亮显示当前顶点组影响到的顶点（权重>0，对标 C4D 点关节显示影响范围）",
    )
    joint_filter_active: bpy.props.BoolProperty(
        name="仅显示影响选中点的关节", default=False,
        description="Joint Filter：列表只显示在选中顶点上有权重的顶点组（隐藏无关骨骼，对标 C4D 关节过滤器）",
    )
    joint_filter_name: bpy.props.StringProperty(
        name="搜索关节", default="", maxlen=63,
        description="Joint Filter：按名称子串过滤顶点组列表",
    )
    weight_hud: bpy.props.BoolProperty(
        name="权重 HUD", default=False,
        description="视口光标旁实时显示当前骨骼在鼠标所指顶点上的权重值（对标 C4D 权重 HUD，仅编辑/权重绘制模式）",
    )
    edge_loop_highlight: bpy.props.BoolProperty(
        name="高亮选中的边环", default=True,
        description="权重绘制模式下用橙色线高亮边环选择选中的边环（权重模式没有原生边高亮）",
    )
    vert_table_verts: bpy.props.CollectionProperty(type=WeightTableVert)
    vert_table_rows: bpy.props.CollectionProperty(type=WeightTableRow)
    vert_table_index: bpy.props.IntProperty(default=0)
    vert_table_row_index: bpy.props.IntProperty(default=0)


# ---------------------------------------------------------------- Operators

class WeightOT_Apply(bpy.types.Operator):
    """把当前权重值设为选中顶点的权重"""
    bl_idname = "weight.apply"
    bl_label = "设置权重到选中点"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None:
            self.report({"WARNING"}, "请先选择/新建一个顶点组")
            return {"CANCELLED"}
        if _vg_locked(vg):
            self.report({"WARNING"}, f"顶点组「{vg.name}」已锁定")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要刷权重的点/面")
            return {"CANCELLED"}
        value = context.scene.weight_manager.weight_value
        n = weight_tools.set_weights(obj, indices, vg.index, value)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"已把 {n} 个顶点权重设为 {value:.3f}（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_Smooth(bpy.types.Operator):
    """平滑选中顶点的权重（邻域平均）"""
    bl_idname = "weight.smooth"
    bl_label = "平滑权重"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要平滑的点/面")
            return {"CANCELLED"}
        n = weight_tools.smooth_weights(obj, indices, vg.index,
                                        radius=context.scene.weight_manager.smooth_radius)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"已平滑 {n} 个顶点的权重（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_Invert(bpy.types.Operator):
    """反转选中顶点的权重（w -> 1-w）"""
    bl_idname = "weight.invert"
    bl_label = "反转权重"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要反转的点/面")
            return {"CANCELLED"}
        n = weight_tools.invert_weights(obj, indices, vg.index)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"已反转 {n} 个顶点的权重（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_Offset(bpy.types.Operator):
    """整体加/减选中顶点的权重"""
    bl_idname = "weight.offset"
    bl_label = "增减权重"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        items=[("INC", "", "加"), ("DEC", "", "减")], default="INC")

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要增减的点/面")
            return {"CANCELLED"}
        delta = context.scene.weight_manager.offset_delta
        if self.mode == "DEC":
            delta = -delta
        n = weight_tools.offset_weights(obj, indices, vg.index, delta)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"已{'加' if delta > 0 else '减'}权重：影响 {n} 个顶点")
        return {"FINISHED"}


class WeightOT_AutoWeight(bpy.types.Operator):
    """C4D 式 Auto Weight：按 Set / Add / Subtract / Smooth 模式统一应用权重"""
    bl_idname = "weight.auto_weight"
    bl_label = "应用"
    bl_description = "按当前模式（Set/Add/Subtract/Smooth）把权重应用到选中点（对标 C4D Auto Weight）"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        settings = context.scene.weight_manager
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要处理的点/面")
            return {"CANCELLED"}
        mode = settings.auto_weight_mode
        if mode == "ABSOLUTE":
            n = weight_tools.set_weights(obj, indices, vg.index, settings.weight_value)
        elif mode == "ADD":
            n = weight_tools.offset_weights(obj, indices, vg.index, settings.offset_delta)
        elif mode == "SUBTRACT":
            n = weight_tools.offset_weights(obj, indices, vg.index, -settings.offset_delta)
        else:  # SMOOTH
            n = weight_tools.smooth_weights(obj, indices, vg.index, radius=settings.smooth_radius)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"Auto Weight[{mode}] 已处理 {n} 个顶点（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_Mirror(bpy.types.Operator):
    """镜像权重：把当前组在一侧（如 +X）顶点的权重整体镜像到另一侧（如 -X）。

    对标 C4D 的镜像：不用先选点，一键把半边刷好的权重复制到对侧对称顶点。
    """
    bl_idname = "weight.mirror"
    bl_label = "镜像权重"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(
        name="镜像方向",
        items=[
            ("PX", "+X→-X", "把 +X 侧顶点的权重镜像到 -X 侧"),
            ("NX", "-X→+X", "把 -X 侧顶点的权重镜像到 +X 侧"),
            ("PY", "+Y→-Y", "把 +Y 侧顶点的权重镜像到 -Y 侧"),
            ("NY", "-Y→+Y", "把 -Y 侧顶点的权重镜像到 +Y 侧"),
            ("PZ", "+Z→-Z", "把 +Z 侧顶点的权重镜像到 -Z 侧"),
            ("NZ", "-Z→+Z", "把 -Z 侧顶点的权重镜像到 +Z 侧"),
        ],
        default="PX",
    )

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        axis = self.direction[1]  # "PX"[1] = "X"（[0] 是方向前缀 P 或 N）
        source_sign = 1 if self.direction[0] == "P" else -1  # P=+侧→-侧, N=-侧→+侧
        n = weight_tools.mirror_weights_side(obj, vg.index, axis=axis, source_sign=source_sign)
        _finish_edit(context, obj, None)
        label = {"PX": "+X→-X", "NX": "-X→+X", "PY": "+Y→-Y", "NY": "-Y→+Y",
                 "PZ": "+Z→-Z", "NZ": "-Z→+Z"}[self.direction]
        self.report({"INFO"}, f"已镜像 {label}：{n} 个对称顶点同步了权重（组「{vg.name}」）")
        return {"FINISHED"}


_copy_buffer = []  # 复制/黏贴：复制的权重值列表（按选中点顺序）


class WeightOT_Copy(bpy.types.Operator):
    """复制权重：把当前顶点组在选中点上的权重值按选中顺序复制下来（对标 C4D 复制）"""
    bl_idname = "weight.copy"
    bl_label = "复制权重"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        global _copy_buffer
        obj = context.active_object
        vg = _active_vg(obj)
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要复制的点/面")
            return {"CANCELLED"}
        _copy_buffer = list(weight_tools._read_all(obj, vg.index, indices))
        self.report({"INFO"}, f"已复制 {len(_copy_buffer)} 个点的权重（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_Paste(bpy.types.Operator):
    """黏贴权重：把复制的权重值按选中顺序写到当前选中点（对标 C4D 黏贴）"""
    bl_idname = "weight.paste"
    bl_label = "黏贴权重"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None and _copy_buffer

    def execute(self, context):
        global _copy_buffer
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None or _vg_locked(vg):
            self.report({"WARNING"}, "顶点组缺失或已锁定")
            return {"CANCELLED"}
        if not _copy_buffer:
            self.report({"WARNING"}, "请先「复制权重」，再黏贴")
            return {"CANCELLED"}
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要黏贴的点/面")
            return {"CANCELLED"}
        # 按选中顺序一一对应；点数不一致时只黏贴前 n 个并提示。
        # 注意：set_weights 是把「同一个标量」赋给所有点，逐点不同的值必须走 _write_all 的 mapping。
        n = min(len(_copy_buffer), len(indices))
        weight_tools._write_all(obj, vg.index,
                                list(zip(indices[:n], _copy_buffer[:n])))
        _finish_edit(context, obj, None)
        msg = f"已黏贴 {n} 个点（组「{vg.name}」）"
        if n != len(_copy_buffer):
            msg += f"；复制了 {len(_copy_buffer)} 个点，本次只选中 {len(indices)} 个"
        elif len(indices) > n:
            msg += f"；选中的点比复制的多，多余的保持原样"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class WeightOT_Normalize(bpy.types.Operator):
    """Normalize 归一化：选中顶点的权重总和设为 1（锁定的骨骼权重保持不变）"""
    bl_idname = "weight.normalize"
    bl_label = "归一化"
    bl_description = ("把选中顶点的所有权重组按比例缩放使总和=1；锁定的骨骼（🔒）权重保持不变，"
                      "只调整其余组（对标 C4D 锁关节归一化）")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok

    def execute(self, context):
        obj = context.active_object
        indices = _get_indices(context, obj)
        if not indices:
            self.report({"WARNING"}, "请先选中要归一化的点/面")
            return {"CANCELLED"}
        locked = {g.index for g in obj.vertex_groups if _vg_locked(g)}
        n = weight_tools.normalize_weights(obj, indices, locked)
        _finish_edit(context, obj, None)
        msg = f"已归一化 {n} 个顶点的权重（总和=1）"
        if locked:
            msg += f"，锁定 {len(locked)} 个骨骼组保持不变"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class WeightOT_SelectWeight(bpy.types.Operator):
    """按权重值选择顶点（C4D 式 Fill Selection）"""
    bl_idname = "weight.select_weight"
    bl_label = "按权重选择"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        items=[
            ("EQ0", "", "权重 = 0"),
            ("GT0", "", "权重 > 0"),
            ("LT1", "", "权重 < 1"),
            ("EQ1", "", "权重 = 1"),
            ("RANGE", "", "权重 ≈ 阈值"),
        ],
        default="GT0",
    )

    @classmethod
    def poll(cls, context):
        ok, _ = _require_mesh_edit(context)
        return ok and _active_vg(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None:
            self.report({"WARNING"}, "请先选择/新建一个顶点组")
            return {"CANCELLED"}
        threshold = context.scene.weight_manager.select_threshold
        sel = weight_tools.select_verts_by_weight(
            obj, vg.index, self.mode, value=threshold)
        if not sel:
            self.report({"INFO"}, f"组「{vg.name}」没有符合该条件的顶点")
            return {"FINISHED"}
        weight_tools.apply_selection(obj, context.mode, sel)
        _finish_edit(context, obj, None)
        self.report({"INFO"}, f"按权重选中 {len(sel)} 个顶点（组「{vg.name}」）")
        return {"FINISHED"}


class WeightOT_PickEdgeLoop(bpy.types.Operator):
    """C4D 式边环选择：面板按钮进入 modal → 在 3D 视口点一条边选中整条边环（编辑/权重绘制模式均可）。

    注意：不注册 Alt+点击 快捷键——权重/顶点绘制模式的 Alt+LMB 是原生选面键
    （view3d.select，mask 开启时），注册会抢不过原生或双重触发，入口只走面板按钮。
    """
    bl_idname = "weight.pick_edge_loop"
    bl_label = "选择边环"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = ("点一下按钮后进入选择模式，在 3D 视口里像编辑模式一样选边：单击选单条边，"
                      "Alt+单击选整条循环边，Shift 加选 / Shift+点击已选边取消（编辑 / 权重绘制模式都能用，"
                      "权重模式没有原生边选择）。Ctrl+单击 选两点间最短路径（编辑 / 权重模式都可，"
                      "Ctrl+Shift 把路径加进现有选择）。选中两条环后用「Fill Select 填充选择」插件填中间面")

    add: bpy.props.BoolProperty(
        name="叠加选择", default=False,
        description="True = 在现有选择上加选（Shift+点击）；False = 只选这条",
    )

    deselect: bpy.props.BoolProperty(
        name="减选", default=False,
        description="True = 从现有选择中减去（Ctrl+点击）；False = 正常选择",
    )

    toggle: bpy.props.BoolProperty(
        name="切换选择", default=False,
        description="True = Shift+点击已选边时取消选择（编辑模式原生 toggle）；False = 正常",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and context.mode in ("EDIT_MESH", "PAINT_WEIGHT")

    def _native_loop_select(self, context, obj, target_idx, add, deselect=False, ring=True, toggle=False):
        """编辑模式原生环选择：`bpy.ops.mesh.loop_multi_select()`（编辑模式
        Alt+点击 同款底层算法，v1.9.10 起替代自定义 _grow_edge_loop）。

        ring=True 时调用前把选择清成「只留目标边」，loop_multi_select 从该边
        扩展出整条环（沿同向边链，和编辑模式 Alt+点击完全一致）；ring=False
        只选目标单边。toggle=True（Shift+点击，v1.9.20）= 编辑模式原生 toggle：
        点击已选边则取消选择、未选则加选；add=True 合并（Shift+点击 加选），
        deselect=True 从已有选择里减去。返回最终选中边索引集合。
        """
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        prev = {e.index for e in bm.edges if e.select} if (add or deselect or toggle) else set()
        if ring:
            for e in bm.edges:
                e.select = False
            bm.edges[target_idx].select = True
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.mesh.loop_multi_select()
            new_sel = {e.index for e in bm.edges if e.select}
        else:
            new_sel = {target_idx}
        if toggle:
            # Shift 点击：已选则减、未选则加（编辑模式原生 toggle）
            final = (prev - new_sel) if (prev & new_sel) else (prev | new_sel)
        elif deselect:
            final = prev - new_sel
        elif add:
            final = prev | new_sel
        else:
            final = new_sel
        for e in bm.edges:
            e.select = e.index in final
        bmesh.update_edit_mesh(obj.data)
        return final

    def _pick_shortest_path(self, bm, target_idx):
        """从活动边（`self._active_edge`，上次点选的边）到目标边的最短路径边集
        （含两端），并把活动边更新为目标边（连续 Ctrl+点击 可沿链延伸）。

        没有活动边 / 活动==目标 / 不连通 → 只选目标边（Dijkstra 返回空/单边时
        不误报）。编辑/权重模式共用；编辑模式在 from_edit_mesh 的 bmesh 上算。
        """
        anchor = getattr(self, "_active_edge", None)
        self._active_edge = target_idx
        if anchor is None or anchor == target_idx:
            return {target_idx}
        path = _shortest_path_edges(bm, anchor, target_idx)
        return set(path) if path else {target_idx}

    def _do_pick(self, context, win_mx, win_my, select_ring, shortest_path=False):
        """窗口坐标 (win_mx, win_my) 处射线选边 → 选边/选环/选路径 → 写回边选中。

        select_ring=True 选整条循环边（编辑模式用原生 `bpy.ops.mesh.loop_multi_select()`，
        权重模式用临时 bmesh 复刻 `_edge_loop_from`）；False 只选鼠标下那条边——
        交互完全对标编辑模式选边（v1.9.20）：单击=单选、Shift=加选/点击已选边则取消
        （toggle）、Alt 选环、Ctrl 最短路径。

        shortest_path=True（v1.9.20 改 Ctrl；v1.9.22 改为连点延伸）：从**上一次点选的边**（活动
        边，`self._active_edge`）到本次点到的边，算**最短路径**（Dijkstra 边长加权，
        `_shortest_path_edges`）并**加进**当前选择（= 按住 Ctrl 连续点击，路径从上次选的边
        一直延伸加长，同编辑模式，不用按 Shift）。权重模式没有原生实现，纯 Python 复刻。
        活动边更新为目标边（`_pick_shortest_path` 内完成）→ 连续 Ctrl+点击沿链延伸。

        返回 {"RUNNING_MODAL"} 让选择模式保持运行（可连续操作，右键/ESC 退出）；
        v1.9.18 点在视口空白处（射线没打到网格）= 取消选择，报告后模态保持。
        win_mx/win_my 是窗口绝对坐标（event.mouse_x/y）。不直接依赖 context.region
        —— 模态操作符里它可能是按钮所在侧栏，不是鼠标下的视口（坐标/视口错配 →
        整条射线射空 → 「没点到网格」）。改为显式找鼠标下的 3D 视口
        （_view3d_ray_from_mouse）。主点 + 周围 ±3px 采样，防止点不到细边。
        """
        obj = context.active_object

        def _try_pick(bm, ray):
            origin, direction = ray
            return _pick_edge_from_ray(obj, bm, origin, direction)

        # v1.9.17 第二轮：主点守卫。鼠标必须真的在 3D 视口 WINDOW 上方才算「点边」，
        # 否则（点在侧栏按钮等 UI 上）PASS_THROUGH 把事件放回 UI，让按钮能响应。
        # 坑（用户实测日志「已选 3 条边 → 没点到网格」）：侧栏按钮若离视口边界 3px 内，
        # 旧版把主点+±3px 角落一起收集，主点在按钮上时角落采样会掉进视口 WINDOW →
        # rays 非空 → 射线射空 → 报「没点到网格」。先要求主点在视口内再采样角落。
        primary = _view3d_ray_from_mouse(context, win_mx, win_my)
        if primary is None:
            # 鼠标不在 3D 视口（比如在侧栏按钮上）→ 别当成「点边失败」报
            # 「没点到网格」，PASS_THROUGH 把事件放回给 UI（侧栏按钮/其它 operator
            # 能正常响应），边环选择 modal 保持运行。旧版在这里 report WARNING 后
            # RUNNING_MODAL，用户边环选择 modal 还开着时点「设置权重到选中点」按钮
            # 被 modal 吃事件 → 一直报「没点到网格」。
            return {"PASS_THROUGH"}
        rays = [primary]
        for dx, dy in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            r = _view3d_ray_from_mouse(context, win_mx + dx, win_my + dy)
            if r is not None:
                rays.append(r)

        target_idx, err = None, None
        was_toggle_remove = False  # Shift+点击已选边 → 报告「（取消选择）」
        if context.mode == "EDIT_MESH":
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            for ray in rays:
                target_idx, err = _try_pick(bm, ray)
                if target_idx is not None:
                    break
            if target_idx is None:
                # v1.9.18 用户要求：选边模式点视口空白处 = 取消选择。清掉边选择
                # + fill 的面选择（同新选边时的清理），高亮消失，模态保持。
                for e in bm.edges:
                    e.select = False
                for p in obj.data.polygons:
                    p.select = False
                bmesh.update_edit_mesh(obj.data)
                area = context.area
                if area:
                    area.tag_redraw()
                self.report({"INFO"}, "已取消选择（点在空白处）")
                return {"RUNNING_MODAL"}
            if shortest_path:
                # v1.9.22 Ctrl 连点延伸：路径始终**加进**现有选择（= 从活动边延伸），
                # 不用按 Shift——编辑模式 Ctrl 连点就是这样，权重模式保持一致。
                sel = {e.index for e in bm.edges if e.select}
                sel |= self._pick_shortest_path(bm, target_idx)
                for e in bm.edges:
                    e.select = e.index in sel
                bmesh.update_edit_mesh(obj.data)
            else:
                was_toggle_remove = self.toggle and bm.edges[target_idx].select
                sel = self._native_loop_select(context, obj, target_idx, self.add,
                                               self.deselect, select_ring, self.toggle)
        else:
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                for ray in rays:
                    target_idx, err = _try_pick(bm, ray)
                    if target_idx is not None:
                        break
                if target_idx is not None:
                    if shortest_path:
                        # v1.9.22 Ctrl 连点延伸：路径始终**加进**现有选择，
                        # 同编辑模式，不用按 Shift。
                        path_sel = {e.index for e in obj.data.edges if e.select}
                        path_sel |= self._pick_shortest_path(bm, target_idx)
                        for i, e in enumerate(obj.data.edges):
                            e.select = i in path_sel
                        for p in obj.data.polygons:
                            p.select = False
                        obj.data.update()
                        area = context.area
                        if area:
                            area.tag_redraw()
                        msg = f"已选最短路径 {len(path_sel)} 条边（延伸）"
                        msg += " · Shift+Q 可填环内面"
                        self.report({"INFO"}, msg)
                        return {"RUNNING_MODAL"}
                    # 权重模式没有原生边选择：临时 bmesh 上复刻原生 loop_select
                    # 算法（_edge_loop_from，逐边验证与 loop_multi_select 一致），
                    # 全程不切 EDIT（用户要求：权重模式直接选环，不切模式）。
                    # 单选时只取目标边。
                    new_sel = _edge_loop_from(bm, target_idx) if select_ring else {target_idx}
            finally:
                bm.free()
            if target_idx is None:
                # v1.9.18 用户要求：权重模式点视口空白处 = 取消选择（同编辑模式）。
                for e in obj.data.edges:
                    e.select = False
                for p in obj.data.polygons:
                    p.select = False
                obj.data.update()
                area = context.area
                if area:
                    area.tag_redraw()
                self.report({"INFO"}, "已取消选择（点在空白处）")
                return {"RUNNING_MODAL"}
            prev = {e.index for e in obj.data.edges if e.select} \
                if (self.add or self.deselect or self.toggle) else set()
            if self.toggle:
                # Shift 点击：已选则减、未选则加（编辑模式原生 toggle）
                was_toggle_remove = bool(prev & new_sel)
                sel = (prev - new_sel) if was_toggle_remove else (prev | new_sel)
            elif self.deselect:
                sel = prev - new_sel
            elif self.add:
                sel = prev | new_sel
            else:
                sel = new_sel
            for i, e in enumerate(obj.data.edges):
                e.select = i in sel
            # v1.9.17 用户反馈「fill 后连选中的边也不亮」：fill 的面选择残留会让
            # _draw_edge_overlay 一直画旧 fill 面轮廓、掩盖后续选边。新的边环选择
            # 开始时清掉 fill 的面选择，高亮回到「当前选中边」。
            for p in obj.data.polygons:
                p.select = False
            obj.data.update()

        area = context.area
        if area:
            area.tag_redraw()
        self._active_edge = target_idx
        if select_ring:
            msg = f"已选边环 {len(sel)} 条边"
        else:
            msg = f"已选 {len(sel)} 条边"
        if self.add:
            msg += "（加选）"
        elif was_toggle_remove:
            msg += "（取消选择）"
        self.report({"INFO"}, msg + " · Shift+Q 可填环内面（按鼠标位置）")
        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        # 一律进模态，等用户在 3D 视口点一条边。
        # 坑（v1.9.5 实测）：面板按钮的 invoke 上下文在 Blender 5 里 region_data 是
        # 有效的（按钮上下文是 3D 视口 WINDOW region）——若在这里用按钮位置立即
        # _do_pick，射线指向按钮所在像素（不在网格上）→ 当场报「没点到网格」，
        # 模态永远等不到用户在视口点边。所以不能有「region_data 有效就立即拾取」的
        # 快速路径，统一走模态。
        context.window_manager.modal_handler_add(self)
        self.add = False
        self.deselect = False
        self.toggle = False
        self.report({"INFO"}, "选择模式：单击选边 · Shift 加选/取消 · "
                    "Alt+单击 选循环边 · Ctrl 最短路径 · 右键/ESC 退出")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            # 和编辑模式选边完全一致（v1.9.20/22）：Ctrl+单击 = 最短路径（从活动边
            # 延伸，Ctrl 连点路径一直加长，不用按 Shift；v1.9.22 改，原 Ctrl+Shift 才
            # 加选）、Alt+单击 = 选环（Alt+Shift 加环）、Shift+单击 = 加选 / 点击已选边
            # 则取消（编辑模式原生 toggle）、单击 = 单选。编辑模式没有 Ctrl 减选，这里也没有。
            if event.ctrl and not event.alt:
                self.add = event.shift
                self.deselect = False
                self.toggle = False
                return self._do_pick(context, event.mouse_x, event.mouse_y,
                                     select_ring=False, shortest_path=True)
            if event.alt:
                # Alt+Shift = 环 toggle（编辑模式 loop_select 带 toggle=True：
                # 点击已选环取消、未选环加环）
                self.add = False
                self.deselect = False
                self.toggle = event.shift
                return self._do_pick(context, event.mouse_x, event.mouse_y,
                                     select_ring=True)
            # 单击 / Shift+单击：Shift = toggle（编辑模式：点击已选边取消选择）
            self.add = False
            self.deselect = False
            self.toggle = event.shift
            return self._do_pick(context, event.mouse_x, event.mouse_y,
                                 select_ring=False)
        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self.report({"INFO"}, "已退出边环选择")
            return {"CANCELLED"}
        # 其它事件（视图旋转/滚轮/中键）透传给原生，保持可浏览
        return {"PASS_THROUGH"}
        return {"RUNNING_MODAL"}


class WeightOT_SelectBoundaryLoop(bpy.types.Operator):
    """选填充面的轮廓边（边界环）：权重模式对标编辑模式「选择边界环」。

    编辑模式原生 `mesh.region_to_loop`（5.0 里 select_boundary_loop 已并入它，
    keymap 无默认快捷键、在 Select 菜单里），权重模式没有 → 纯 Python 复刻
    `_boundary_loop_edges`（恰好 1 个邻面被选中的边）。Fill Select 填充后点按钮，
    把填充区域的轮廓边选出来（边高亮 + 后续可 Shift+Q 再填/配合选边）。
    """
    bl_idname = "weight.select_boundary_loop"
    bl_label = "选择填充面轮廓边"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and context.mode in ("EDIT_MESH", "PAINT_WEIGHT")

    def execute(self, context):
        obj = context.active_object
        b_edges = _boundary_loop_edges(obj)
        if not b_edges:
            self.report({"WARNING"}, "请先选中面（Fill Select 填充后点这里选轮廓边）")
            return {"CANCELLED"}
        if context.mode == "EDIT_MESH":
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            for e in bm.edges:
                e.select = e.index in b_edges
            for f in bm.faces:
                f.select = False
            bmesh.update_edit_mesh(obj.data)
        else:
            # 权重模式写 mesh 层（无 bmesh）；清面选择让高亮回到「当前选中边」
            # （同 _do_pick 选边时的清理，fill 面残留不掩盖轮廓边高亮）。
            for i, e in enumerate(obj.data.edges):
                e.select = i in b_edges
            for p in obj.data.polygons:
                p.select = False
            obj.data.update()
        self.report({"INFO"}, f"已选填充面轮廓边 {len(b_edges)} 条 · Ctrl+单击 可沿轮廓延伸路径")
        return {"FINISHED"}


class WeightOT_GroupNew(bpy.types.Operator):
    """新建顶点组，并把当前选中顶点加入（权重设为当前权重值）"""
    bl_idname = "weight.group_new"
    bl_label = "新建顶点组"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        obj = context.active_object
        # 自动编号组名
        base, i = "Group", 1
        names = {g.name for g in obj.vertex_groups}
        while f"{base}.{i:03d}" in names:
            i += 1
        vg = obj.vertex_groups.new(name=f"{base}.{i:03d}")
        obj.vertex_groups.active_index = len(obj.vertex_groups) - 1
        # 编辑模式下把选中顶点加入新组
        if context.mode in ("EDIT_MESH", "PAINT_WEIGHT"):
            indices = _get_indices(context, obj)
            if indices:
                value = context.scene.weight_manager.weight_value
                weight_tools.set_weights(obj, indices, vg.index, value)
                _finish_edit(context, obj, None)
        self.report({"INFO"}, f"已新建顶点组「{vg.name}」")
        return {"FINISHED"}


class WeightOT_GroupDelete(bpy.types.Operator):
    """删除激活顶点组"""
    bl_idname = "weight.group_delete"
    bl_label = "删除顶点组"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.vertex_groups

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        if vg is None:
            return {"CANCELLED"}
        name = vg.name
        obj.vertex_groups.remove(vg)
        self.report({"INFO"}, f"已删除顶点组「{name}」")
        return {"FINISHED"}


class WeightOT_GroupRename(bpy.types.Operator):
    """重命名激活顶点组"""
    bl_idname = "weight.group_rename"
    bl_label = "重命名顶点组"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.vertex_groups

    def execute(self, context):
        obj = context.active_object
        vg = _active_vg(obj)
        new = context.scene.weight_manager.rename_to.strip()
        if vg is None:
            return {"CANCELLED"}
        if not new:
            self.report({"WARNING"}, "请输入新名称")
            return {"CANCELLED"}
        old = vg.name
        vg.name = new
        context.scene.weight_manager.rename_to = ""
        self.report({"INFO"}, f"顶点组「{old}」→「{new}」")
        return {"FINISHED"}


# ---------------------------------------------------------------- 列表控件

class WM_UL_VertexGroups(bpy.types.UIList):
    """顶点组（骨骼）列表，对标 C4D Weight Manager 的 Joints 列表。"""

    def filter_items(self, context, data, property):
        """Joint Filter 关节过滤器：仅显示影响选中点的关节 / 按名称搜索。"""
        settings = context.scene.weight_manager
        sel = []
        # 影响过滤器依赖「选中顶点」：只在编辑/权重模式下取选择；OBJECT 模式选中区不存在，
        # 取残留选择会导致列表按过期数据过滤（且 _get_indices 在 OBJECT 模式开销无意义）。
        if settings.joint_filter_active and context.mode in ("EDIT_MESH", "PAINT_WEIGHT"):
            sel = _get_indices(context, data)
        return _joint_filter_flags(
            data, sel, settings.joint_filter_name,
            settings.joint_filter_active, self.bitflag_filter_item), []

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        vg = item
        obj = data
        row = layout.row(align=True)
        row.label(text=vg.name, icon="GROUP_BONE")
        lock_prop = "lock_weight" if hasattr(vg, "lock_weight") else ("lock" if hasattr(vg, "lock") else None)
        if lock_prop:
            row.prop(vg, lock_prop, text="",
                      icon="LOCKED" if _vg_locked(vg) else "UNLOCKED", emboss=False)
        # 百分比条：每行右侧展示当前组在选中顶点上的平均权重（对标 C4D Joints 列表的小色条）。
        # 不能用共享 FloatProperty 每行写入——Blender 在 draw_item 全部结束后才渲染按钮值，
        # 共享属性会被最后一行覆盖，导致所有行显示同一个值；VertexGroup 又不支持动态属性，
        # 所以用 row.split() 自绘比例条：值当场算、当场按比例切分两格，每行独立正确。
        if context.mode in ("EDIT_MESH", "PAINT_WEIGHT") and obj.type == "MESH":
            pv = _ul_weight_preview(context, obj, vg)
            if pv > 0.0:
                split = row.split(factor=min(0.98, pv), align=True)
                split.box().label(text=" ")
                split.box().label(text=" ")


class WM_UL_WeightVerts(bpy.types.UIList):
    """顶点权重表·顶点列表：当前选中顶点，行 = 顶点编号，点选决定「激活顶点」。"""

    def filter_items(self, context, data, property):
        return [], []   # 同步函数已只放选中顶点，全显

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text="", icon="VERTEXSEL")
        row.label(text=f"顶点 {item.vert_index}")


class WM_UL_WeightRows(bpy.types.UIList):
    """顶点权重表·骨骼权重列表：激活顶点的所有骨骼 + 每行可拖权重滑条（按权重降序）。

    每行是一个独立 WeightTableRow 实例（有自己的 weight 属性）——不是共享 FloatProperty，
    不会出现所有行显示同一个值的问题（Bug B 的教训）。锁定组行置灰（enabled=False）。
    """

    def filter_items(self, context, data, property):
        return [], []

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # 注意：data 是 settings（rows 的 template_list 绑在 settings.vert_table_rows 上），
        # 没有 vertex_groups——必须从 context.active_object 拿骨骼（早期版本误用
        # data.vertex_groups，GUI 里 AttributeError 每行刷屏）。
        obj = context.active_object
        gi = item.group_index
        vg = obj.vertex_groups[gi] if (obj and 0 <= gi < len(obj.vertex_groups)) else None
        locked = _vg_locked(vg) if vg is not None else True
        row = layout.row(align=True)
        if locked:
            row.enabled = False   # 锁定骨骼整行只读
        row.label(text=vg.name if vg is not None else "?", icon="GROUP_BONE")
        # 精度在 WeightTableRow.weight 的 FloatProperty(precision=3) 定义里，
        # UILayout.prop() 不接收 precision 关键字（Blender 4.x/5.x 都不接收，传了就 TypeError）。
        row.prop(item, "weight", text="", slider=True)


# ---------------------------------------------------------------- 面板

class VIEW3D_PT_WeightManager(bpy.types.Panel):
    bl_label = "Weight Manager 权重管理器"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Weight Mgr"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        settings = context.scene.weight_manager
        mode = context.mode
        can_edit = mode in ("EDIT_MESH", "PAINT_WEIGHT")
        vg = _active_vg(obj)

        # 版本号标签（排查边环选择问题时用来确认加载的是新版）
        row = layout.row(align=True)
        row.label(text="v" + ".".join(str(x) for x in ADDON_VERSION), icon="INFO")
        row.separator()

        # ---------- 权重绘制模式：选择遮罩开关（对标 C4D 权重模式下能看线框/选点选面） ----------
        if mode == "PAINT_WEIGHT":
            box = layout.box()
            box.label(text="选择遮罩（Blender 原生，开了才能在权重模式看线框/选点选面）", icon="RESTRICT_SELECT_OFF")
            row = box.row(align=True)
            row.prop(obj.data, "use_paint_mask", text="面遮罩", icon="FACESEL", toggle=True)
            row.prop(obj.data, "use_paint_mask_vertex", text="点遮罩", icon="VERTEXSEL", toggle=True)
            box.label(text="Alt+左键 选面 · Shift+Alt 加选 · B 框选 · A 全选", icon="MOUSE_LMB")
            if obj.data.use_paint_mask_vertex:
                box.label(text="点遮罩：未选中顶点显示为黑（正常），先框选/点选顶点再刷", icon="INFO")
            # 权重模式看清网格：Blender 原生线框 overlay（未刷权重的网格默认是深色，
            # 开线框才能看清边缘在哪）
            sp = getattr(context, "space_data", None)
            if sp is not None and hasattr(sp, "overlay"):
                row = box.row(align=True)
                row.label(text="看不清？开线框", icon="SHADING_WIRE")
                row.prop(sp.overlay, "show_wireframes", text="显示线框", toggle=True)
                if not sp.overlay.show_wireframes:
                    box.label(text="提示：权重模式未刷权重的网格是深色，开线框能看清边", icon="INFO")
            # 笔刷镜像（对称）已删除：面板开关点了对实际笔刷无效果（用户实测），
            # 用 Blender 自带笔刷镜像（3D 视口顶部笔刷旁的 X/Y/Z 按钮）。

            # ---------- C4D 式边环选择（权重模式没有原生边选择；入口用按钮 modal——
            #          不注册 Alt+点击，那个键在权重模式是原生选面，冲突） ----------
            box = layout.box()
            box.label(text="边环选择（C4D 式，权重模式可用）", icon="EDGESEL")
            row = box.row(align=True)
            row.operator("weight.pick_edge_loop", text="进入选边模式", icon="RESTRICT_SELECT_OFF")
            row.prop(settings, "edge_loop_highlight", text="高亮边环", icon="HIDE_OFF", toggle=True)
            # v1.9.21：Fill Select 填面后选轮廓边（权重模式对标编辑模式「选择边界环」）
            row = box.row(align=True)
            row.operator("weight.select_boundary_loop", text="选填充面轮廓边", icon="EDGESEL")
            box.label(text="单击选边 · Shift 加选/点击已选边取消 · Alt+单击 选环 · "
                      "Ctrl+单击 最短路径（同编辑模式）", icon="MOUSE_LMB")

        # ---------- 顶点组（骨骼）列表 + 管理（对标 C4D Joints 列表） ----------
        box = layout.box()
        box.label(text="顶点组（骨骼）", icon="GROUP_VERTEX")
        # Joint Filter 关节过滤器（对标 C4D：只显示影响选中点的关节 / 按名称搜索）
        row = box.row(align=True)
        row.prop(settings, "joint_filter_active", text="仅显示影响选中点的关节", icon="FILTER", toggle=True)
        row = box.row(align=True)
        row.prop(settings, "joint_filter_name", text="", placeholder="搜索骨骼名…")
        if settings.joint_filter_active and mode not in ("EDIT_MESH", "PAINT_WEIGHT"):
            box.label(text="（需编辑/权重模式才能按选中点过滤，先选中点/面）", icon="INFO")
        # 影响范围高亮（对标 C4D：点关节 → 视口高亮它的影响范围）
        row = box.row(align=True)
        row.prop(settings, "influence_highlight", text="高亮当前组影响范围", icon="RESTRICT_SELECT_OFF", toggle=True)
        # 权重 HUD（光标旁权重值，对标 C4D 视口 HUD）
        row = box.row(align=True)
        row.prop(settings, "weight_hud", text="权重 HUD（光标权重值）", icon="HIDE_OFF", toggle=True)
        box.template_list(
            "WM_UL_VertexGroups", "", obj, "vertex_groups",
            obj.vertex_groups, "active_index", rows=4)
        if vg is not None and _vg_locked(vg):
            box.label(text=f"「{vg.name}」已锁定", icon="INFO")
        row = box.row(align=True)
        row.operator("weight.group_new", text="新建", icon="ADD")
        row.operator("weight.group_delete", text="删除", icon="X")
        row = box.row(align=True)
        row.prop(settings, "rename_to", text="")
        row.operator("weight.group_rename", text="重命名")

        if vg is None:
            layout.label(text="先新建/选择一个顶点组", icon="ERROR")
            return

        # ---------- Auto Weight（对标 C4D 的 Auto Weight：模式 + 权重条二合一） ----------
        box = layout.box()
        box.label(text="Auto Weight", icon="MODIFIER_ON")
        locked = _vg_locked(vg)
        if not can_edit or locked:
            box.enabled = False
            box.label(text="（进入编辑/权重绘制模式，并解锁组）", icon="INFO")
        row = box.row(align=True)
        row.prop(settings, "auto_weight_mode", expand=True)
        # 选中点统计
        if can_edit and not locked:
            indices = _get_indices(context, obj)
            stats = weight_tools.weight_stats(obj, indices, vg.index) if indices else None
            if stats:
                box.label(
                    text=f"{stats[0]} 顶点 · {stats[1]:.2f}–{stats[2]:.2f} · 均 {stats[3]:.2f}",
                    icon="INFO")
            else:
                box.label(text="未选中点/面（先选中再拖条）", icon="RESTRICT_SELECT_OFF")

        mode = settings.auto_weight_mode
        if mode == "ABSOLUTE":
            # 原生横向大滑条：点哪跳到哪、拖动实时改值，直接把选中点权重设为对应值
            pct = f"{settings.weight_value * 100:.0f}%"
            row = box.row()
            row.scale_y = 2.2
            row.prop(settings, "weight_value", text=pct, slider=True)
            row = box.row(align=True)
            row.operator("weight.apply", text="设置权重到选中点")
            row.operator("weight.select_weight", text="全选本组").mode = "GT0"
        else:
            # Add / Subtract / Smooth：原生滑条 —— 可拖动、也支持悬停滚轮（Blender 滑条原生行为），
            # 按变动幅度持续叠加/叠减/平滑，方向不影响，应用后自动归零，可反复叠加
            row = box.row(align=True)
            row.prop(settings, "offset_delta", text="Strength")
            row = box.row()
            row.scale_y = 2.2
            mode_label = {"ADD": "Add 叠加", "SUBTRACT": "Subtract 叠减", "SMOOTH": "Smooth 平滑"}[mode]
            row.prop(settings, "drag_bar", text=f"拖 动 / Ctrl+滚轮 · {mode_label}", slider=True)
            if mode == "SMOOTH":
                row = box.row(align=True)
                row.prop(settings, "smooth_radius", text="Smooth 半径（影响范围）")
            row = box.row(align=True)
            row.operator("weight.auto_weight", text="应用一次（按 Strength）", icon="PLAY")
            row.operator("weight.select_weight", text="全选本组").mode = "GT0"

        # ---------- Commands（独立命令：反转 / 镜像 / 复制黏贴） ----------
        box = layout.box()
        box.label(text="Commands", icon="SETTINGS")
        if not can_edit or locked:
            box.enabled = False
        row = box.row(align=True)
        row.operator("weight.invert", text="反转", icon="ARROW_LEFTRIGHT")
        # 镜像：整组一键把一侧权重镜像到对侧对称顶点（对标 C4D 镜像，不用先选点）
        row = box.row(align=True)
        row.operator("weight.mirror", text="+X→-X").direction = "PX"
        row.operator("weight.mirror", text="-X→+X").direction = "NX"
        row = box.row(align=True)
        row.operator("weight.mirror", text="+Y→-Y").direction = "PY"
        row.operator("weight.mirror", text="-Y→+Y").direction = "NY"
        row = box.row(align=True)
        row.operator("weight.mirror", text="+Z→-Z").direction = "PZ"
        row.operator("weight.mirror", text="-Z→+Z").direction = "NZ"
        # 复制/黏贴权重（对标 C4D：复制当前组在选中点上的权重，换选点后黏贴，按选中顺序一一对应）
        row = box.row(align=True)
        row.operator("weight.copy", text="复制权重", icon="COPYDOWN")
        row.operator("weight.paste", text="黏贴权重", icon="PASTEDOWN")

        # ---------- Normalize 归一化（对标 C4D：锁关节后其余按比例归一化） ----------
        box = layout.box()
        box.label(text="Normalize 归一化", icon="CHECKMARK")
        if not can_edit:
            box.enabled = False
        row = box.row(align=True)
        row.operator("weight.normalize", text="归一化选中点（总和=1）")
        row.label(text="🔒", icon="LOCKED")
        row.label(text="锁定组不动")


        # ---------- 按权重填充选择 ----------
        box = layout.box()
        box.label(text="按权重选择", icon="RESTRICT_SELECT_OFF")
        if not can_edit:
            box.enabled = False
        row = box.row(align=True)
        for op_id, label in (("EQ0", "=0"), ("GT0", ">0"), ("LT1", "<1"), ("EQ1", "=1")):
            op = row.operator("weight.select_weight", text=label); op.mode = op_id
        row = box.row(align=True)
        row.prop(settings, "select_threshold", text="阈值")
        op = row.operator("weight.select_weight", text="≈区间"); op.mode = "RANGE"

        # ---------- 联动 Fill Select 填充选择插件 ----------
        box = layout.box()
        box.label(text="填充选择", icon="FACE_MAPS")
        fill_op = _fill_select_op()
        if fill_op is not None:
            box.operator(fill_op, text="填充选择 (U+F)")
            box.label(text="选中两条环 → 选中中间面 → 上面拖条刷权重", icon="INFO")
        else:
            col = box.column()
            col.enabled = False
            col.label(text="未安装「Fill Select 填充选择」插件", icon="ERROR")
            col.label(text="需要它来选中边界环之间的面", icon="QUESTION")

        # ---------- 顶点权重表（选中点 → 所有骨骼权重数字，可编辑，对标 Maya Component Editor） ----------
        if can_edit:
            _sync_weight_table(context, obj, settings)
            box = layout.box()
            box.label(text="顶点权重表", icon="FILE_TEXT")
            if settings.vert_table_verts:
                row = box.row()
                row.template_list(
                    "WM_UL_WeightVerts", "", settings, "vert_table_verts",
                    settings, "vert_table_index", rows=4)
                if settings.vert_table_rows:
                    box.template_list(
                        "WM_UL_WeightRows", "", settings, "vert_table_rows",
                        settings, "vert_table_row_index", rows=6)
                else:
                    box.label(text="（该顶点没有任何骨骼权重）", icon="INFO")
            else:
                box.label(text="先选中顶点/面（编辑或权重模式）", icon="RESTRICT_SELECT_OFF")


# ---------------------------------------------------------------- 注册

_classes = (
    WeightTableVert,
    WeightTableRow,
    WeightManagerSettings,
    WM_UL_VertexGroups,
    WM_UL_WeightVerts,
    WM_UL_WeightRows,
    WeightOT_Apply,
    WeightOT_Smooth,
    WeightOT_Invert,
    WeightOT_Offset,
    WeightOT_AutoWeight,
    WeightOT_Mirror,
    WeightOT_Copy,
    WeightOT_Paste,
    WeightOT_Normalize,
    WeightOT_SelectWeight,
    WeightOT_PickEdgeLoop,
    WeightOT_SelectBoundaryLoop,
    WeightOT_GroupNew,
    WeightOT_GroupDelete,
    WeightOT_GroupRename,
    VIEW3D_PT_WeightManager,
)


def register():
    global _registered, _draw_handle, _hud_handle, _edge_handle
    if _registered:
        return  # 本副本已注册（同一进程重复 enable），直接跳过
    # 惰性保护：任何同名类已存在于 bpy.types → 说明传统副本或扩展副本已注册，
    # 本副本完全跳过（不注册类 / 不设 Scene.weight_manager / 不加 overlay）。
    if any(hasattr(bpy.types, _bpy_type_name(cls)) for cls in _classes):
        return
    _registered = True
    for cls in _classes:
        if hasattr(bpy.types, _bpy_type_name(cls)):
            continue  # 双保险：逐类跳过已注册的（正常走不到，防御而已）
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            if "already registered" not in str(e):
                raise
    if not hasattr(bpy.types.Scene, "weight_manager"):
        bpy.types.Scene.weight_manager = bpy.props.PointerProperty(type=WeightManagerSettings)
    # 视口影响范围高亮 overlay（无头/极老环境挂不上就跳过，不影响插件其它功能）
    try:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_influence_overlay, (), "WINDOW", "POST_VIEW")
    except Exception:
        _draw_handle = None
    # 视口权重 HUD（光标旁权重值；同上，挂不上就跳过）
    try:
        _hud_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_weight_hud, (), "WINDOW", "POST_PIXEL")
    except Exception:
        _hud_handle = None
    # 视口边环高亮 overlay（权重模式补边高亮；同上，挂不上就跳过）
    try:
        _edge_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_edge_overlay, (), "WINDOW", "POST_VIEW")
    except Exception:
        _edge_handle = None
    # 权重模式 Shift+Q 填充（和编辑模式一致）：Fill Select 插件（mesh.fill_select）
    # 只在 "Mesh" keymap 注册 Shift+Q，编辑模式才激活；权重绘制模式（"Weight Paint"
    # keymap）按了没反应。这里给 Weight Paint keymap 补注册 Shift+Q → fill_select，
    # 让「选两条边环 → Shift+Q 填中间面」在权重模式和编辑模式操作一致。fill_select
    # 的 poll 本来就允许 PAINT_WEIGHT（_EDITABLE_MODES = ("EDIT_MESH", "PAINT_WEIGHT")），
    # 未安装 Fill Select 时 _fill_select_op() 返回 None，不注册。冲突：权重模式下
    # Shift+Q 无原生绑定，不冲突；编辑模式下 Mesh keymap 的 Shift+Q（Fill Select 自己）
    # 优先，这里不重复注册。
    # 无条件注册：keymap item 在按键时才解析 operator，fill_select 未装时惰性无效，
    # 之后装好（或换官方扩展版后重启用本插件）就自动生效，与两个插件的启用顺序无关。
    fill_op = _fill_select_op() or "mesh.fill_select"  # 未装时用传统版 idname 兜底
    try:
        kc = bpy.context.window_manager.keyconfigs.addon
        if kc is not None:
            km = kc.keymaps.new(name="Weight Paint", space_type="EMPTY")
            kmi = km.keymap_items.new(fill_op, "Q", "PRESS", shift=True)
            _keymaps.append((km, kmi))
    except Exception:
        pass
    # 不注册边环选择快捷键：权重/顶点绘制模式的 Alt+LMB（view3d.select）是原生选面键，
    # 注册 Alt+点击 会与之冲突（原生 PRESS 先消费事件，我们的 CLICK 可能双重触发）。
    # 入口只走面板按钮 → modal，任何模式都无冲突。


def unregister():
    global _registered, _draw_handle, _hud_handle, _edge_handle
    if not _registered:
        return  # 本副本从未注册（惰性副本 / 已被别处注销），什么都不碰
    _registered = False
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None
    if _hud_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_hud_handle, "WINDOW")
        except Exception:
            pass
        _hud_handle = None
    if _edge_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_edge_handle, "WINDOW")
        except Exception:
            pass
        _edge_handle = None
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is not None:
        for km, kmi in _keymaps:
            try:
                km.keymap_items.remove(kmi)
            except Exception:
                pass
    _keymaps.clear()
    if hasattr(bpy.types.Scene, "weight_manager"):
        del bpy.types.Scene.weight_manager
    for cls in reversed(_classes):
        if not hasattr(cls, "bl_rna"):
            continue  # 该副本从没注册过这个类（防御：部分注册失败时不留脏状态）
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
    print("[WeightManager] 插件已注册。3D 视口按 N 打开侧栏，切到 Weight Mgr。")
