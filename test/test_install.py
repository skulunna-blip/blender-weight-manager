# -*- coding: utf-8 -*-
"""安装验证：复现 Preferences > Install 流程，确认 zip 可装、可识别、可启用。"""
import bpy
import os
import sys
import addon_utils
import shutil

ZIP = r"C:\Users\hasee\blender-weight-manager\weight_manager.zip"
checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))
    print(f"[check] {'PASS' if cond else 'FAIL'} {name} {detail}")


# 1. 清掉可能已装的 weight_manager 文件夹
target = os.path.join(bpy.utils.user_resource("SCRIPTS"), "addons")
existing = os.path.join(target, "weight_manager")
if os.path.exists(existing):
    shutil.rmtree(existing)

# 2. 用 Preferences 的 Install 流程安装 zip
res = bpy.ops.preferences.addon_install(filepath=ZIP, target="DEFAULT")
check("addon_install 成功", "FINISHED" in str(res), str(res))

# 3. 刷新插件扫描
bpy.ops.preferences.addon_refresh()

# 4. 模块被识别（快速解析能读到）
mods = [m.__name__ for m in addon_utils.modules() if m.__name__ == "weight_manager"]
check("zip 安装后模块被识别", len(mods) == 1, str(mods))

# 5. 启用
ok = addon_utils.enable("weight_manager", default_set=True, persistent=True)
check("插件 enable", ok)

# 6. 关键：确认 bl_info 没有被「误判」（docstring 里含 bl_info 行会导致解析失败）
wm_mod = addon_utils.modules()
bl = next((m.bl_info for m in wm_mod if m.__name__ == "weight_manager"), None)
check("模块有 bl_info", bl is not None, str(bl))

# 7. operator 注册
check("operator weight.apply 注册", hasattr(bpy.ops.weight, "apply"))
check("operator weight.smooth 注册", hasattr(bpy.ops.weight, "smooth"))
check("operator weight.mirror 注册", hasattr(bpy.ops.weight, "mirror"))

# 8. 面板注册
check("面板注册", hasattr(bpy.types, "VIEW3D_PT_WeightManager"))

failed = [c for c in checks if not c[1]]
print(f"[check] PASS {sum(1 for c in checks if c[1])}/{len(checks)}")
if failed:
    print("[check] FAIL")
    sys.exit(1)
print("[check] ALL PASS")
