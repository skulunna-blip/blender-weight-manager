# -*- coding: utf-8 -*-
"""端到端验证：真实 addon 环境，启用 weight_manager 插件后调用 operator。"""
import os
import sys

import bpy
import addon_utils

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # 让 addon_utils 能 import 到 weight_manager 包

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))
    print(f"[check] {'PASS' if cond else 'FAIL'} {name} {detail}")


# ---------- 1. 先建场景/物体（read_factory_settings 会清空插件注册，顺序重要） ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2, size=2)
obj = bpy.context.active_object
vg = obj.vertex_groups.new(name="Bone_A")
right = [i for i, v in enumerate(obj.data.vertices) if v.co.x > 0.5]

# ---------- 2. 启用插件 ----------
ok = addon_utils.enable("weight_manager", default_set=True, persistent=True)
check("插件 enable", ok)
check("Scene.weight_manager 属性注册", hasattr(bpy.types.Scene, "weight_manager"))

# ---------- 3. operator / 面板注册 ----------
for attr in ("apply", "smooth", "invert", "offset", "mirror", "normalize",
             "select_weight", "group_new", "group_delete", "group_rename",
             "auto_weight"):
    check(f"operator weight.{attr} 注册", hasattr(bpy.ops.weight, attr))
check("面板 VIEW3D_PT_WeightManager 注册", hasattr(bpy.types, "VIEW3D_PT_WeightManager"))

# ---------- 3b. Fill Select 存在性检测（自注册临时类验证，不依赖用户是否装了扩展） ----------
# 旧代码用 hasattr(bpy.ops.mesh, "fill_select") 判断——bpy.ops 命名空间对任意字符串都
# 动态生成属性（恒为 True，假阳性），已改用 bpy.types 检查。这里自注册临时 operator 类
# 覆盖「未安装 / 传统版 / 扩展版」三种状态，验证检测函数返回正确 idname。
from weight_manager import _fill_select_op as _fso  # noqa: E402
check("fill_select 检测：无扩展时返回 None（不再恒为 True）", _fso() is None, str(_fso()))

class _FakeMeshFS(bpy.types.Operator):
    bl_idname = "mesh.fill_select"  # 真名，factory reset 后无冲突
    bl_label = "Fill Select (fake)"
    def execute(self, context): return {"FINISHED"}
bpy.utils.register_class(_FakeMeshFS)
check("fill_select 检测：传统版注册后返回 mesh.fill_select", _fso() == "mesh.fill_select", str(_fso()))
bpy.utils.unregister_class(_FakeMeshFS)
check("fill_select 检测：传统版注销后返回 None", _fso() is None, str(_fso()))

class _FakeBlExtFS(bpy.types.Operator):
    bl_idname = "bl_ext.fill_select_between"
    bl_label = "Fill Select Between (fake)"
    def execute(self, context): return {"FINISHED"}
bpy.utils.register_class(_FakeBlExtFS)
check("fill_select 检测：扩展版注册后返回 bl_ext.fill_select_between", _fso() == "bl_ext.fill_select_between", str(_fso()))
bpy.utils.unregister_class(_FakeBlExtFS)
check("fill_select 检测：扩展版注销后返回 None", _fso() is None, str(_fso()))

# ---------- 3c. 新增设置属性（SMOOTH 半径 / 列表百分比条展示值） ----------
_settings = bpy.context.scene.weight_manager
check("smooth_radius 属性注册（Smooth 影响范围）", hasattr(_settings, "smooth_radius"))
check("ul_weight_preview 属性注册（列表百分比条展示值）", hasattr(_settings, "ul_weight_preview"))
check("smooth_radius 默认=1", getattr(_settings, "smooth_radius", -1) == 1, str(getattr(_settings, "smooth_radius", None)))

# ---------- 4. 编辑模式：全选 → 设置权重 ----------
bpy.context.tool_settings.mesh_select_mode = (True, False, False)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
settings = bpy.context.scene.weight_manager
settings.weight_value = 0.7
res = bpy.ops.weight.apply()
check("weight.apply 成功", res == {"FINISHED"}, str(res))
ws = [vg.weight(i) for i in right]
check("apply 后右列权重=0.7", all(abs(w - 0.7) < 1e-6 for w in ws), str(ws))

# ---------- 5. 反转 ----------
res = bpy.ops.weight.invert()
check("weight.invert 成功", res == {"FINISHED"}, str(res))
ws = [vg.weight(i) for i in right]
check("invert 后右列权重=0.3", all(abs(w - 0.3) < 1e-6 for w in ws), str(ws))

# ---------- 6. 增减 ----------
settings.offset_delta = 0.2
res = bpy.ops.weight.offset(mode="INC")
check("weight.offset+ 成功", res == {"FINISHED"}, str(res))
ws = [vg.weight(i) for i in right]
check("offset+ 后右列权重=0.5", all(abs(w - 0.5) < 1e-6 for w in ws), str(ws))

# ---------- 7. 平滑 ----------
res = bpy.ops.weight.smooth()
check("weight.smooth 成功", res == {"FINISHED"}, str(res))

# ---------- 8. 镜像（v1.9.9 起整组定向 +X→-X，默认 direction=PX，不用选点） ----------
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_all(action="SELECT")  # 保持全选即可
res = bpy.ops.weight.mirror()
check("weight.mirror 成功", res == {"FINISHED"}, str(res))
left = [i for i, v in enumerate(obj.data.vertices) if v.co.x < -0.5]
wl = [vg.weight(i) for i in left]
check("mirror 后左列有非零权重", any(abs(w) > 1e-6 for w in wl), str(wl))

# ---------- 9. 按权重选择 ----------
res = bpy.ops.weight.select_weight(mode="EQ0")
check("weight.select_weight 成功", res == {"FINISHED"}, str(res))

# ---------- 9b. Auto Weight（Absolute / Add / Subtract / Smooth） ----------
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.mesh.select_all(action="SELECT")
settings.auto_weight_mode = "ABSOLUTE"
settings.weight_value = 0.4
res = bpy.ops.weight.auto_weight()
check("auto_weight ABSOLUTE 成功", res == {"FINISHED"}, str(res))
check("auto_weight ABSOLUTE 后右列权重=0.4",
      all(abs(vg.weight(i) - 0.4) < 1e-6 for i in right), str([vg.weight(i) for i in right]))

settings.auto_weight_mode = "ADD"
settings.offset_delta = 0.3
res = bpy.ops.weight.auto_weight()
check("auto_weight ADD 成功", res == {"FINISHED"}, str(res))
check("auto_weight ADD 后右列权重=0.7",
      all(abs(vg.weight(i) - 0.7) < 1e-6 for i in right), str([vg.weight(i) for i in right]))

settings.auto_weight_mode = "SUBTRACT"
settings.offset_delta = 0.5
res = bpy.ops.weight.auto_weight()
check("auto_weight SUBTRACT 成功", res == {"FINISHED"}, str(res))
check("auto_weight SUBTRACT 后右列权重=0.2",
      all(abs(vg.weight(i) - 0.2) < 1e-6 for i in right), str([vg.weight(i) for i in right]))

settings.auto_weight_mode = "SMOOTH"
res = bpy.ops.weight.auto_weight()
check("auto_weight SMOOTH 成功", res == {"FINISHED"}, str(res))

# SMOOTH 带 radius=2（影响范围更大）执行成功
settings.smooth_radius = 2
res = bpy.ops.weight.auto_weight()
check("auto_weight SMOOTH 带 radius=2 成功", res == {"FINISHED"}, str(res))
settings.smooth_radius = 1  # 复位

# ---------- 9c. 拖动叠加条 = 原生滑条属性（settings.drag_bar），拖动 or 悬停滚轮都是走同一条属性赋值
# 路径，所以直接对属性赋值即可真实触发 _on_drag_bar 回调（不是像旧 modal 那样只能复现算法）。
# 模拟来回拖动/滚动多次 tick：数值有正有负，但都应按幅度持续叠加（方向不影响，只看变动了多少），
# 且每次应用后应自动归零（可以无限次继续叠加）。
settings.auto_weight_mode = "ADD"
settings.offset_delta = 0.3
from weight_manager import weight_tools as _wt  # noqa: E402  ROOT 已在 sys.path 里（见文件顶部）
set_weights_reset = _wt.set_weights(obj, right, vg.index, 0.0)
ticks = [0.4, -0.25, 0.1]  # 来回拖动/滚动：方向不同，但都应累加（只看幅度）
total_expected = sum(abs(t) * settings.offset_delta for t in ticks)
for t in ticks:
    settings.drag_bar = t
    check(f"drag_bar 赋值 {t} 后自动归零", settings.drag_bar == 0.0, str(settings.drag_bar))
ws = [vg.weight(i) for i in right]
check("drag_bar 拖动叠加条：来回拖动/滚动仍持续叠加（方向不影响）",
      all(abs(w - min(1.0, total_expected)) < 1e-6 for w in ws),
      f"expected={total_expected}, got={ws}")

# 赋值 0 不应有任何效果（早退），也不应报错
before = [vg.weight(i) for i in right]
settings.drag_bar = 0.0
check("drag_bar=0 不改变权重（早退）", [vg.weight(i) for i in right] == before)

# ---------- 9d. 真实权重绘制模式（PAINT_WEIGHT）回归测试 ----------
# Blender 里 object.mode_set(mode="WEIGHT_PAINT") 是切模式用的枚举名，但真正切进去后
# context.mode 读出来其实是 "PAINT_WEIGHT"（不是 "WEIGHT_PAINT"！），这是两套不同的命名。
# 早前代码在 _require_mesh_edit / can_edit / group_new 里都错判成了 "WEIGHT_PAINT"，
# 导致真实权重绘制模式下所有 operator 的 poll 全部失败、面板一直灰掉——这段测试专门堵住这个回归。
bpy.ops.object.mode_set(mode="OBJECT")
for v in obj.data.vertices:
    v.select = v.index in right
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
check("真实权重绘制模式下 context.mode == 'PAINT_WEIGHT'",
      bpy.context.mode == "PAINT_WEIGHT", bpy.context.mode)
settings.weight_value = 0.55
res = bpy.ops.weight.apply()
check("权重绘制模式下 weight.apply 成功（回归：曾因 mode 字符串写错而一直失败）",
      res == {"FINISHED"}, str(res))
check("权重绘制模式下 apply 后右列权重=0.55",
      all(abs(vg.weight(i) - 0.55) < 1e-6 for i in right), str([vg.weight(i) for i in right]))
settings.auto_weight_mode = "ADD"
settings.offset_delta = 0.1
res = bpy.ops.weight.auto_weight()
check("权重绘制模式下 auto_weight 成功", res == {"FINISHED"}, str(res))
bpy.ops.object.mode_set(mode="EDIT")

# ---------- 10. 新建 / 重命名 / 删除顶点组 ----------
res = bpy.ops.weight.group_new()
check("weight.group_new 成功", res == {"FINISHED"}, str(res))
names = [g.name for g in obj.vertex_groups]
check("group_new 创建了新组", len(names) == 2, str(names))

settings.rename_to = "Bone_B_renamed"
res = bpy.ops.weight.group_rename()
check("weight.group_rename 成功", res == {"FINISHED"}, str(res))
check("组已重命名", any(g.name == "Bone_B_renamed" for g in obj.vertex_groups),
      str([g.name for g in obj.vertex_groups]))

bpy.ops.object.mode_set(mode="OBJECT")
obj.vertex_groups.active_index = 1
res = bpy.ops.weight.group_delete()
check("weight.group_delete 成功", res == {"FINISHED"}, str(res))
check("删除后剩 1 组", len(obj.vertex_groups) == 1, str([g.name for g in obj.vertex_groups]))

# ---------- 9e. Normalize 归一化（锁定组保持，对标 C4D 锁关节归一化） ----------
bpy.ops.object.mode_set(mode="OBJECT")
vgB = obj.vertex_groups.new(name="Bone_B")
_wt.set_weights(obj, right, vg.index, 0.2)
_wt.set_weights(obj, right, vgB.index, 0.4)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
res = bpy.ops.weight.normalize()
check("weight.normalize 成功", res == {"FINISHED"}, str(res))
check("normalize 后右列总和≈1",
      all(abs(vg.weight(i) + vgB.weight(i) - 1.0) < 1e-4 for i in right),
      str([(vg.weight(i), vgB.weight(i)) for i in right]))
# 锁定 B 再归一化：B 保持 0.4，A 补足到 0.6
bpy.ops.object.mode_set(mode="OBJECT")
_wt.set_weights(obj, right, vg.index, 0.2)
_wt.set_weights(obj, right, vgB.index, 0.4)
lock_prop = "lock_weight" if hasattr(vgB, "lock_weight") else "lock"
setattr(vgB, lock_prop, True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
res = bpy.ops.weight.normalize()
check("normalize 带锁定执行成功", res == {"FINISHED"}, str(res))
check("normalize 锁定组保持（B 仍 0.4）",
      all(abs(vgB.weight(i) - 0.4) < 1e-6 for i in right))
check("normalize 锁定后 A 补足到 0.6",
      all(abs(vg.weight(i) - 0.6) < 1e-4 for i in right))
setattr(vgB, lock_prop, False)
bpy.ops.object.mode_set(mode="OBJECT")

# ---------- 9f. Joint Filter 关节过滤器 + 影响范围高亮 ----------
from weight_manager import _joint_filter_flags as _jff  # noqa: E402
from weight_manager import _influence_coords as _ifc  # noqa: E402
from weight_manager import _draw_handle as _dh  # noqa: E402
from weight_manager import WM_UL_VertexGroups  # noqa: E402
# 构造：Bone_A 影响右列(0.6)+左列(0.5)，Bone_B 只影响右列(0.4)
# 注意：前面 normalize 把中间列（x=0）顶点归一化成了 1.0，先清掉，保证断言确定
center_col = [i for i, v in enumerate(obj.data.vertices) if abs(v.co.x) < 0.5]
_wt.set_weights(obj, right, vg.index, 0.6)
_wt.set_weights(obj, left, vg.index, 0.5)
_wt.set_weights(obj, center_col, vg.index, 0.0)
_wt.set_weights(obj, right, vgB.index, 0.4)
_wt.set_weights(obj, left, vgB.index, 0.0)
_wt.set_weights(obj, center_col, vgB.index, 0.0)
check("influence_highlight 属性注册", hasattr(_settings, "influence_highlight"))
check("joint_filter_active 属性注册", hasattr(_settings, "joint_filter_active"))
check("joint_filter_name 属性注册", hasattr(_settings, "joint_filter_name"))


def _shown(flags):
    return [g.name for f, g in zip(flags, obj.vertex_groups) if f]


fl = _jff(obj, list(right), name_filter="bone_b")
check("Joint Filter 名称过滤：只剩 Bone_B", _shown(fl) == ["Bone_B"], str(_shown(fl)))
fl2 = _jff(obj, list(left), influence_only=True)
check("Joint Filter 影响过滤：左列只显示 Bone_A（Bone_B 无左列权重）",
      _shown(fl2) == ["Bone_A"], str(_shown(fl2)))
fl3 = _jff(obj, [], influence_only=True)
check("Joint Filter 无选中时显示全部", all(fl3), str(fl3))
fl4 = _jff(obj, list(right), influence_only=True)
check("Joint Filter 右列两组都有影响 → 全显示", all(fl4), str(_shown(fl4)))
fl5 = _jff(obj, list(right), name_filter="bone", influence_only=True)
check("Joint Filter 名称+影响组合过滤", _shown(fl5) == ["Bone_A", "Bone_B"], str(_shown(fl5)))

# 影响范围高亮数据源：Bone_A 影响右+左列，Bone_B 只影响右列
coords_a = _ifc(obj, vg.index)
coords_b = _ifc(obj, vgB.index)
check("影响范围：Bone_A 高亮右+左列", len(coords_a) == len(right) + len(left), f"got={len(coords_a)}")
check("影响范围：Bone_B 只高亮右列", len(coords_b) == len(right), f"got={len(coords_b)}")
check("影响范围：draw handler 已注册", _dh is not None, str(_dh))

# 真实路径：filter_items（编辑模式全选 → 两组都有影响 → 全显示）
# 无头环境不能实例化 UIList（bpy_struct.__new__ 报错），用代理对象走未绑定方法即可测到
# filter_items 的真实代码路径（_get_indices 提取选择 + self.bitflag_filter_item）
class _ULProxy:
    bitflag_filter_item = 1
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
_settings.joint_filter_active = True
_settings.joint_filter_name = ""
flags = WM_UL_VertexGroups.filter_items(_ULProxy(), bpy.context, obj, "vertex_groups")[0]
check("filter_items 全选时两组都显示", all(flags), str(_shown(flags)))
_settings.joint_filter_active = False
_settings.joint_filter_name = ""
bpy.ops.object.mode_set(mode="OBJECT")

# ---------- 11. disable → enable 循环不抛错 ----------
addon_utils.disable("weight_manager")
check("插件 disable", addon_utils.enable("weight_manager", default_set=True))

# ---------- 汇总 ----------
failed = [c for c in checks if not c[1]]
for name, cond, detail in checks:
    print(f"[check] {'PASS' if cond else 'FAIL'} {name} {detail}")
print(f"[check] PASS {sum(1 for c in checks if c[1])}/{len(checks)}")
if failed:
    print("[check] FAIL")
    sys.exit(1)
print("[check] ALL PASS")
