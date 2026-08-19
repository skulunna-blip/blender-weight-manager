# -*- coding: utf-8 -*-
"""核心算法：C4D 式权重管理器的操作逻辑。

性能与兼容性约定：
- 权重读写统一走 bmesh 的 deform layer（底层是 Blender C++ 引擎），
  编辑模式下直接写 bmesh 再 update_edit_mesh，绕开
  「Blender 5.0 禁止在编辑模式调用 VertexGroup.add()」的限制；
- 只读邻接/坐标时，编辑模式复用 live bmesh，其它模式用 bmesh 副本；
- 数据批量读取一次、批量写入一次，避免逐顶点 Python↔C 调用。

约定：所有函数基于「mesh 顶点索引」操作，便于无头单元测试。
"""
import bpy
import bmesh
import mathutils


# ---------------------------------------------------------------- 低层读写

def _replace_many(vg, pairs):
    """非编辑模式下的批量写入（VertexGroup.add 的 weight 只接受标量，逐顶点）。"""
    for i, w in pairs:
        vg.add([i], w, "REPLACE")


def _weight(vg, i):
    """安全读取顶点权重。Blender 5 对不在组中的顶点抛 RuntimeError，返回 0.0。"""
    try:
        return vg.weight(i)
    except RuntimeError:
        return 0.0


def _get_bm(obj, with_deform=True):
    """返回 (bm, deform_layer)。编辑模式复用 live bmesh，其它模式用 bmesh 副本。

    调用方负责：编辑模式结束时 bmesh.update_edit_mesh(obj.data)；
    副本模式结束时 bm.to_mesh(obj.data) + bm.free()。
    """
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    d = bm.verts.layers.deform.verify() if with_deform else None
    return bm, d


def _finish_bm(obj, bm):
    """把 bmesh 改动同步回 mesh。"""
    if obj.mode == "EDIT":
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()


def _read_all(obj, vg_idx, indices):
    """批量读权重。编辑模式走 bmesh deform layer，其它走 VertexGroup。"""
    if obj.mode == "EDIT":
        bm, d = _get_bm(obj)
        return [bm.verts[i][d].get(vg_idx, 0.0) for i in indices]
    vg = obj.vertex_groups[vg_idx]
    return [_weight(vg, i) for i in indices]


def _write_all(obj, vg_idx, mapping):
    """批量写权重。mapping: list of (vert_index, weight)。
    编辑模式写 bmesh deform layer 再同步回 mesh（Blender 5 禁编辑模式调 VertexGroup.add）。
    """
    if not mapping:
        return 0
    if obj.mode == "EDIT":
        bm, d = _get_bm(obj)
        for i, w in mapping:
            bm.verts[i][d][vg_idx] = w
        _finish_bm(obj, bm)
    else:
        _replace_many(obj.vertex_groups[vg_idx], mapping)
    return len(mapping)


# ---------------------------------------------------------------- 选择提取

def selected_vertex_indices(obj, mode, select_mode):
    """返回当前选中顶点的索引列表。

    mode: context.mode（'EDIT_MESH' / 'PAINT_WEIGHT' / ...）
    select_mode: tuple(verts, edges, faces)，来自 tool_settings.mesh_select_mode
    """
    if mode == "EDIT_MESH":
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        sel = set()
        if select_mode[2]:          # 面选择：取选中面的顶点
            for f in bm.faces:
                if f.select:
                    sel.update(v.index for v in f.verts)
        elif select_mode[1]:        # 边选择：取选中边的顶点
            for e in bm.edges:
                if e.select:
                    sel.update(v.index for v in e.verts)
        else:                       # 点选择
            for v in bm.verts:
                if v.select:
                    sel.add(v.index)
        return sorted(sel)

    # 权重绘制 / 物体等模式：mesh 层选择。
    # 🔴 虚拟态坑（v1.9.17 探针实测）：非编辑模式下 mesh.vertices.select 默认全 True，
    # 权重模式直接读它会把「没选过」当「全网格」。且插件边环选择只写 edges.select
    # （_do_pick 权重模式分支）、Fill Select 填面只写 polygons.select（且不清 edges）。
    # 所以按「面 → 边 → 顶点 → 全网格」fallback，让边环选择 / fill 后的权重编辑
    # （设置权重到选中点、absolute/add 滑条）精确作用于边/面的顶点：
    #   - 面部分选中（fill 填面后）→ 选中面的顶点
    #   - 边部分选中（边环选择后，faces 还是虚拟全 True）→ 选中边的顶点
    #   - 顶点部分选中（Blender 权重模式顶点选择工具）→ 选中顶点
    #   - 全部选中（默认虚拟态 / 真全选 / fill 全选）→ 全网格（fill 全选=全网格）
    #   - 全不选 → 空
    mesh = obj.data
    verts, edges, polys = mesh.vertices, mesh.edges, mesh.polygons
    nv, ne, nf = len(verts), len(edges), len(polys)
    v_sel = sum(1 for v in verts if v.select)
    e_sel = sum(1 for e in edges if e.select)
    f_sel = sum(1 for p in polys if p.select)
    if 0 < f_sel < nf:                       # Fill Select 填面 → 面顶点
        return sorted({vi for p in polys if p.select for vi in p.vertices})
    if 0 < e_sel < ne:                       # 边环选择 → 边顶点
        return sorted({vi for e in edges if e.select for vi in e.vertices})
    if 0 < v_sel < nv:                       # 顶点选择工具 → 顶点
        return [i for i, v in enumerate(verts) if v.select]
    if v_sel == nv:                          # 默认虚拟态 / 全选 → 全网格
        return list(range(nv))
    return []


def apply_selection(obj, mode, indices):
    """把 indices 应用到网格选择（edit mode 走 bmesh，其它模式走 mesh）。"""
    idx = set(indices)
    if mode == "EDIT_MESH":
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for v in bm.verts:
            v.select = v.index in idx
        # 边/面 select 完全由顶点推导，避免 select_flush_mode 连带选中边界
        for e in bm.edges:
            e.select = all(v.index in idx for v in e.verts)
        for f in bm.faces:
            f.select = all(v.index in idx for v in f.verts)
        bmesh.update_edit_mesh(obj.data)
    else:
        for v in obj.data.vertices:
            v.select = v.index in idx


# ---------------------------------------------------------------- 权重读写

def set_weights(obj, indices, vg_idx, value):
    """把选中顶点权重设为 value（绝对值，对标 C4D 的权重值字段）。"""
    if not indices:
        return 0
    return _write_all(obj, vg_idx, [(i, value) for i in indices])


def read_weights(obj, indices, vg_idx):
    return _read_all(obj, vg_idx, indices)


def weight_stats(obj, indices, vg_idx):
    """返回 (count, wmin, wmax, wavg)，无选中返回 None。"""
    ws = _read_all(obj, vg_idx, indices)
    if not ws:
        return None
    return (len(ws), min(ws), max(ws), sum(ws) / len(ws))


# ---------------------------------------------------------------- 工具

def offset_weights(obj, indices, vg_idx, delta):
    """整体加/减权重（钳制到 0..1）。"""
    if not indices:
        return 0
    ws = _read_all(obj, vg_idx, indices)
    return _write_all(obj, vg_idx,
                      [(i, min(1.0, max(0.0, w + delta))) for i, w in zip(indices, ws)])


def invert_weights(obj, indices, vg_idx):
    """反转权重：w -> 1 - w。"""
    if not indices:
        return 0
    ws = _read_all(obj, vg_idx, indices)
    return _write_all(obj, vg_idx, [(i, 1.0 - w) for i, w in zip(indices, ws)])


def smooth_weights(obj, indices, vg_idx, iterations=1, factor=1.0, radius=1):
    """平滑：每个选中顶点权重 = 原权重 + (邻域平均权重 - 原权重) * factor。

    radius: 邻域扩展层数（对标 C4D Smooth 的半径/影响范围）。
            1 = 只取直接相邻顶点（默认，保持旧行为）；
            2/3/... = 沿边向外扩展更多层，影响范围更大、平滑更彻底。
    """
    if not indices:
        return 0
    bm, d = _get_bm(obj)
    bm.edges.ensure_lookup_table()
    for _ in range(iterations):
        mapping = []
        for i in indices:
            v = bm.verts[i]
            # BFS 收集 radius 层内邻域顶点
            seen = {v.index}
            frontier = [v]
            for _depth in range(radius):
                nxt = []
                for cur in frontier:
                    for e in cur.link_edges:
                        o = e.other_vert(cur)
                        if o.index not in seen:
                            seen.add(o.index)
                            nxt.append(o)
                frontier = nxt
            nbrs = [bm.verts[j] for j in seen if j != i]
            if not nbrs:
                continue
            wi = v[d].get(vg_idx, 0.0)
            avg = sum(n[d].get(vg_idx, 0.0) for n in nbrs) / len(nbrs)
            mapping.append((i, wi + (avg - wi) * factor))
        for i, w in mapping:
            bm.verts[i][d][vg_idx] = w
    _finish_bm(obj, bm)
    return len(indices)


def mirror_weights(obj, indices, vg_idx, axis="X", threshold=1e-3):
    """镜像权重：把每个选中顶点的权重写到其「空间对称顶点」（以对象原点为对称中心）。

    双向安全：选中顶点若其对称点就是它自己（对称轴上的点），写自己无副作用。
    """
    if not indices:
        return 0
    axis_i = {"X": 0, "Y": 1, "Z": 2}[axis]
    bm, d = _get_bm(obj)
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for v in bm.verts:
        kd.insert(v.co, v.index)
    kd.balance()
    pairs = {}
    for i in indices:
        co = bm.verts[i].co.copy()
        co[axis_i] = -co[axis_i]
        _c, idx, dist = kd.find(co)
        if idx != -1 and dist <= threshold:
            pairs[idx] = bm.verts[i][d].get(vg_idx, 0.0)
    for i, w in pairs.items():
        bm.verts[i][d][vg_idx] = w
    _finish_bm(obj, bm)
    return len(pairs)


def mirror_weights_side(obj, vg_idx, axis="X", source_sign=1, threshold=1e-3):
    """沿 axis 把一侧顶点的权重整体镜像到对侧（对标 C4D 镜像：+X→-X 等）。

    source_sign=+1：把 co[axis]>0 侧顶点的权重复制到对称顶点（- 侧）；
    source_sign=-1 则相反。轴上的点（co[axis]≈0）跳过。不需要先选中点。
    """
    axis_i = {"X": 0, "Y": 1, "Z": 2}[axis]
    bm, d = _get_bm(obj)
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for v in bm.verts:
        kd.insert(v.co, v.index)
    kd.balance()
    pairs = {}
    for v in bm.verts:
        c = v.co[axis_i]
        if source_sign > 0 and c <= threshold:
            continue
        if source_sign < 0 and c >= -threshold:
            continue
        co = v.co.copy()
        co[axis_i] = -co[axis_i]
        _c, idx, dist = kd.find(co)
        if idx != -1 and dist <= threshold:
            pairs[idx] = v[d].get(vg_idx, 0.0)
    for i, w in pairs.items():
        bm.verts[i][d][vg_idx] = w
    _finish_bm(obj, bm)
    return len(pairs)


def normalize_weights(obj, indices, vg_locked=None):
    """Normalize 归一化：把选中顶点的所有权重组按比例缩放，使总和 = 1。

    vg_locked: 锁定的顶点组索引集合（保持权重不变，只调整其他组）。
               对标 C4D「锁住对应骨骼的权重，其余关节按比例归一化」：
               例如某顶点 A=0.2、B=0.4（锁定 B），归一化后 B 仍 0.4，A 补足到 0.6。
    """
    if not indices:
        return 0
    vg_locked = vg_locked or set()
    bm, d = _get_bm(obj)
    bm.verts.ensure_lookup_table()
    changed = 0
    for i in indices:
        v = bm.verts[i]
        weights = dict(v[d])  # {组索引: 权重}
        if not weights:
            continue
        locked_sum = sum(w for g, w in weights.items() if g in vg_locked)
        unlocked = [g for g in weights if g not in vg_locked]
        unlocked_sum = sum(weights[g] for g in unlocked)
        target = max(0.0, 1.0 - locked_sum)
        if target <= 1e-9 or unlocked_sum <= 1e-9:
            continue  # 锁定已占满 / 无非锁定权重可调
        scale = target / unlocked_sum
        for g in unlocked:
            nw = max(0.0, weights[g] * scale)
            if nw > 1e-9:
                v[d][g] = nw
            elif g in v[d]:
                del v[d][g]  # 移除权重归零的条目
        changed += 1
    _finish_bm(obj, bm)
    return changed


def group_has_influence(obj, vg_idx, indices):
    """顶点组是否在给定顶点上至少有一个权重 > ε（Joint Filter 关节过滤器用）。"""
    if not indices:
        return False
    return any(w > 1e-4 for w in _read_all(obj, vg_idx, indices))


# ---------------------------------------------------------------- 按权重选择

def select_verts_by_weight(obj, vg_idx, op, value=0.5, tol=0.005):
    """按权重选择顶点索引，对标 C4D 的 Fill Selection。

    op: 'EQ0'(=0) 'GT0'(>0) 'LT1'(<1) 'EQ1'(=1) 'RANGE'(≈value±tol)
    """
    if obj.mode == "EDIT":
        bm, d = _get_bm(obj)
        weights = [bm.verts[i][d].get(vg_idx, 0.0) for i in range(len(bm.verts))]
    else:
        vg = obj.vertex_groups[vg_idx]
        weights = [_weight(vg, i) for i in range(len(obj.data.vertices))]
    out = []
    for i, w in enumerate(weights):
        if op == "EQ0" and w <= 1e-6:
            out.append(i)
        elif op == "GT0" and w > 1e-6:
            out.append(i)
        elif op == "LT1" and w < 1.0 - 1e-6:
            out.append(i)
        elif op == "EQ1" and w >= 1.0 - 1e-6:
            out.append(i)
        elif op == "RANGE" and abs(w - value) <= tol:
            out.append(i)
    return out
