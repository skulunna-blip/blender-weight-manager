# -*- coding: utf-8 -*-
"""最小环境验证：Blender 无头能跑、顶点组 API 可用。
用法: blender --background --python test/env_probe.py
"""
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.active_object
assert obj.type == "MESH"

# 顶点组 API 验证
vg = obj.vertex_groups.new(name="Bone_A")
vg.add([0, 1, 2], 0.5, "REPLACE")
assert abs(vg.weight(0) - 0.5) < 1e-6, vg.weight(0)

# add 带权重索引
vg.add([3], 0.25, "REPLACE")
assert abs(vg.weight(3) - 0.25) < 1e-6

# 读取 mesh 顶点组数据
mesh = obj.data
print("[env] vertex_groups:", [g.name for g in obj.vertex_groups])
print("[env] v0 groups:", [(g.group, g.weight) for g in mesh.vertices[0].groups])
print("[env] n_verts:", len(mesh.vertices))

# edit mode 下 bmesh 可用
bpy.ops.object.mode_set(mode="EDIT")
import bmesh
bm = bmesh.from_edit_mesh(obj.data)
bm.verts.ensure_lookup_table()
print("[env] bmesh n_verts:", len(bm.verts))
bmesh.update_edit_mesh(obj.data)
bpy.ops.object.mode_set(mode="OBJECT")

# 无头模式是否有 addon keyconfigs（用于快捷键注册判断）
print("[env] keyconfigs.addon:", bpy.context.window_manager.keyconfigs.addon is not None)

print("[env] PASS")
