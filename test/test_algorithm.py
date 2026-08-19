# -*- coding: utf-8 -*-
"""算法单元验证：直接测 weight_tools 的纯函数，不依赖 UI/插件注册。"""
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weight_manager"))

import bpy
import bmesh
from weight_tools import (
    set_weights, invert_weights, offset_weights, smooth_weights,
    mirror_weights, normalize_weights, group_has_influence,
    select_verts_by_weight, weight_stats,
    selected_vertex_indices, apply_selection,
)

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def grid(obj):
    """x∈{-1,0,1}, y∈{-1,0,1} 的 3x3 平面。"""
    vs = obj.data.vertices
    right = [i for i, v in enumerate(vs) if v.co.x > 0.5]
    left = [i for i, v in enumerate(vs) if v.co.x < -0.5]
    center = [i for i, v in enumerate(vs) if abs(v.co.x) < 0.5 and abs(v.co.y) < 0.5]
    return right, left, center


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------- set / invert / offset ----------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2, size=2)
obj = bpy.context.active_object
vg = obj.vertex_groups.new(name="Bone_A")
right, left, center = grid(obj)

set_weights(obj, right, vg.index, 0.8)
check("set_weights 设权重", all(abs(vg.weight(i) - 0.8) < 1e-6 for i in right))

invert_weights(obj, right, vg.index)
check("invert 反转", all(abs(vg.weight(i) - 0.2) < 1e-6 for i in right))

offset_weights(obj, right, vg.index, 0.3)
check("offset 加 0.3", all(abs(vg.weight(i) - 0.5) < 1e-6 for i in right))

offset_weights(obj, right, vg.index, -0.7)
check("offset 减并钳制到 0", all(abs(vg.weight(i)) < 1e-6 for i in right))

offset_weights(obj, right, vg.index, 9.0)
check("offset 钳制上限 1", all(abs(vg.weight(i) - 1.0) < 1e-6 for i in right))

st = weight_stats(obj, right, vg.index)
check("weight_stats 统计", st is not None and st[0] == 3 and abs(st[2] - 1.0) < 1e-6, str(st))

# ---------- select by weight ----------
# 先把全部顶点入组，避免「未分组顶点被当作权重 0」干扰断言
set_weights(obj, list(range(9)), vg.index, 0.5)
set_weights(obj, left, vg.index, 0.0)
set_weights(obj, center, vg.index, 1.0)
set_weights(obj, right, vg.index, 0.8)
sel_eq0 = select_verts_by_weight(obj, vg.index, "EQ0")
sel_gt0 = select_verts_by_weight(obj, vg.index, "GT0")
sel_eq1 = select_verts_by_weight(obj, vg.index, "EQ1")
sel_range = select_verts_by_weight(obj, vg.index, "RANGE", value=0.8)
check("select EQ0 选左列(权重0)", set(sel_eq0) == set(left))
check("select GT0 选权重>0", set(sel_gt0) == {i for i in range(9) if i not in set(left)})
check("select EQ1 选中心(权重1)", set(sel_eq1) == set(center))
check("select RANGE 阈值0.8", set(sel_range) == set(right))

# ---------- smooth ----------
set_weights(obj, list(range(9)), vg.index, 0.0)  # 全部清零，保证中心邻域全 0
set_weights(obj, center, vg.index, 1.0)
smooth_weights(obj, center, vg.index)
check("smooth 中心邻域全0 -> 中心变0",
      abs(vg.weight(center[0])) < 1e-6, f"center={vg.weight(center[0])}")

# ---------- smooth radius（半径影响范围） ----------
# 3x3 grid：中心 (0,0)；radius=1 邻域 = 上下左右 4 个相邻（全 0）；
# radius=2 邻域额外含 4 个对角（设 0.8）。验证半径扩展后平滑结果不同。
vs = obj.data.vertices
idx = {(round(v.co.x, 3), round(v.co.y, 3)): i for i, v in enumerate(vs)}
c_i = idx[(0.0, 0.0)]
adj = [idx[(0, 1)], idx[(0, -1)], idx[(1, 0)], idx[(-1, 0)]]
diag = [idx[(1, 1)], idx[(1, -1)], idx[(-1, 1)], idx[(-1, -1)]]
set_weights(obj, list(range(9)), vg.index, 0.0)
set_weights(obj, [c_i], vg.index, 1.0)
set_weights(obj, diag, vg.index, 0.8)
smooth_weights(obj, [c_i], vg.index, radius=1)
r1 = vg.weight(c_i)
set_weights(obj, [c_i], vg.index, 1.0)  # 重置中心，再测 radius=2
smooth_weights(obj, [c_i], vg.index, radius=2)
r2 = vg.weight(c_i)
check("smooth radius=1 只取相邻(全0) -> 中心=0",
      abs(r1) < 1e-6, f"r1={r1}")
check("smooth radius=2 邻域含对角(0.8) -> 中心≈0.4（(0*4+0.8*4)/8）",
      abs(r2 - 0.4) < 1e-4, f"r2={r2}")
# 半径 1 和 2 结果必须不同，证明 radius 参数真实生效
check("smooth radius 参数真实影响结果（r1≠r2）", abs(r1 - r2) > 0.1, f"r1={r1}, r2={r2}")

# ---------- mirror ----------
set_weights(obj, right, vg.index, 0.8)
set_weights(obj, left, vg.index, 0.0)
n = mirror_weights(obj, right, vg.index, axis="X")
check("mirror 复制右->左", all(abs(vg.weight(i) - 0.8) < 1e-6 for i in left), f"mirrored={n}")

# ---------- normalize（归一化，锁定组保持） ----------
# 场景：中心顶点在两组上叠加 A=0.2、B=0.4（总和 0.6）。
# 不锁定时按比例归一化（A=1/3, B=2/3）；锁定 B 时 B 保持 0.4，A 补足到 0.6。
vgB = obj.vertex_groups.new(name="Bone_B")
for g in (vg, vgB):
    set_weights(obj, list(range(9)), g.index, 0.0)
set_weights(obj, center, vg.index, 0.2)
set_weights(obj, center, vgB.index, 0.4)
normalize_weights(obj, center, set())
wA = vg.weight(center[0]); wB = vgB.weight(center[0])
check("normalize 非锁定：A/B 按比例缩放且总和=1",
      abs(wA - 1 / 3) < 1e-4 and abs(wB - 2 / 3) < 1e-4 and abs(wA + wB - 1.0) < 1e-6,
      f"A={wA}, B={wB}")
set_weights(obj, center, vg.index, 0.2)
set_weights(obj, center, vgB.index, 0.4)
normalize_weights(obj, center, {vgB.index})
wA = vg.weight(center[0]); wB = vgB.weight(center[0])
check("normalize 锁定 B：B 保持 0.4，A 补足到 0.6（总和=1）",
      abs(wA - 0.6) < 1e-4 and abs(wB - 0.4) < 1e-6 and abs(wA + wB - 1.0) < 1e-6,
      f"A={wA}, B={wB}")

# ---------- group_has_influence（Joint Filter 关节过滤器用） ----------
# 重建清晰状态：vg 影响右列(0.8)+vgB 右列(0.4)，左列两组都是 0
for g in (vg, vgB):
    set_weights(obj, list(range(9)), g.index, 0.0)
set_weights(obj, right, vg.index, 0.8)
set_weights(obj, right, vgB.index, 0.4)
check("group_has_influence 右列 vg 有影响", group_has_influence(obj, vg.index, right))
check("group_has_influence 右列 vgB 有影响", group_has_influence(obj, vgB.index, right))
check("group_has_influence 左列 vg 无影响", not group_has_influence(obj, vg.index, left))
check("group_has_influence 左列 vgB 无影响", not group_has_influence(obj, vgB.index, left))
check("group_has_influence 空列表 → False", not group_has_influence(obj, vg.index, []))

# ---------- edit mode 选择提取（cube：面选择模式选顶面 = 4 个顶点） ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.active_object
cube.vertex_groups.new(name="G")
bpy.ops.object.mode_set(mode="EDIT")
bpy.context.tool_settings.mesh_select_mode = (False, False, True)  # 面选择
bm = bmesh.from_edit_mesh(cube.data)
for v in bm.verts:
    v.select = False
for e in bm.edges:
    e.select = False
for f in bm.faces:
    f.select = f.calc_center_median().z > 0.5
bmesh.update_edit_mesh(cube.data)
sm = tuple(bpy.context.tool_settings.mesh_select_mode)
indices = selected_vertex_indices(cube, "EDIT_MESH", sm)
check("edit 面选择提取顶面4顶点",
      len(indices) == 4 and all(cube.data.vertices[i].co.z > 0.5 for i in indices),
      f"got={sorted(indices)}")
# apply_selection 回写（重新只选顶面顶点，face 亮显应推导一致）
apply_selection(cube, "EDIT_MESH", indices)
bm2 = bmesh.from_edit_mesh(cube.data)
face_ok = all(f.select == (f.calc_center_median().z > 0.5) for f in bm2.faces)
check("apply_selection 回写面选择", face_ok)
bpy.ops.object.mode_set(mode="OBJECT")

# ---------- 汇总 ----------
failed = [c for c in checks if not c[1]]
for name, cond, detail in checks:
    print(f"[check] {'PASS' if cond else 'FAIL'} {name} {detail}")
print(f"[check] PASS {sum(1 for c in checks if c[1])}/{len(checks)}")
if failed:
    print("[check] FAIL")
    sys.exit(1)
print("[check] ALL PASS")
