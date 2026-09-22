extends Node
## 自检：右上角菜单里的「作弊器」。
##   1) 菜单里有没有这一项、点开是不是这块面板
##   2) 改铜钱：逻辑值、money_tishi、画面上那一格数字是不是一起变
##   3) 改盗窃成功率 cc、以及「全部拉满」
##   4) 关掉之后游戏按键恢复
##
## 用法：python -X utf8 tools/run_probe.py dev/cheat_probe.tscn
const SHOT_DIR := "res://../截图预览/作弊器"

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._goto(268)
	main._drain()
	main.logic.setv("money", 1000)
	main.logic.setv("money_tishi", "1000文")
	main.logic.setv("cc", 3)
	main._render()
	await _settle(4)

	var labels := []
	for b in main.tools._menu.get_children():
		labels.append((b as Button).text)
	print("[作弊] 菜单项：%s" % ", ".join(labels))

	main.tools._on_menu_item("作弊器")
	await _settle(4)
	print("[作弊] 打开：modal=%s ui_open=%s 面板可见=%s" % [main.tools._modal, str(main.tools.ui_open()), str(main.tools._cheat_box.visible)])
	print("[作弊] 面板矩形=%s" % str(main.tools._cheat_box.get_global_rect()))
	print("[作弊] 面板最小尺寸=%s" % str(main.tools._cheat_box.get_combined_minimum_size()))
	for c in main.tools._cheat_box.get_child(0).get_children():
		if c is Label:
			print("[作弊]   文字行 rect=%s 内容=%s" % [str((c as Label).get_global_rect()), (c as Label).text.left(24)])
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))
	get_viewport().get_texture().get_image().save_png("%s/菜单里的作弊器.png" % SHOT_DIR)
	for v in main.tools._cheat_edit:
		print("[作弊]   输入框 %-6s 当前值=（%s）" % [v, (main.tools._cheat_edit[v] as LineEdit).text])

	print("[作弊] ---- 改铜钱 88888 ----")
	(main.tools._cheat_edit["money"] as LineEdit).text = "88888"
	main.tools._on_cheat_set("money")
	await _settle(6)
	print("[作弊]   逻辑 money=%s money_tishi=%s" % [str(main.logic.V("money")), str(main.logic.V("money_tishi"))])
	print("[作弊]   画面数字=%s" % _shown("money_tishi"))

	print("[作弊] ---- 改 cc=4 ----")
	(main.tools._cheat_edit["cc"] as LineEdit).text = "4"
	main.tools._on_cheat_set("cc")
	await _settle(4)
	print("[作弊]   逻辑 cc=%s" % str(main.logic.V("cc")))

	print("[作弊] ---- 全部拉满 ----")
	main.tools._on_cheat_fill()
	await _settle(4)
	print("[作弊]   cc=%s ZG_JL=%s xiuwei=%s hp=%s WLT=%s" % [str(main.logic.V("cc")),
			str(main.logic.V("ZG_JL")), str(main.logic.V("xiuwei")), str(main.logic.V("hp")), str(main.logic.V("WLT"))])

	print("[作弊] ---- 铜钱 +10000 ----")
	main.tools._on_cheat_money(10000)
	await _settle(4)
	print("[作弊]   money=%s" % str(main.logic.V("money")))

	print("[作弊] ---- 非数字输入 ----")
	(main.tools._cheat_edit["money"] as LineEdit).text = "abc"
	main.tools._on_cheat_set("money")
	await _settle(2)
	print("[作弊]   money 没被改坏：%s" % str(main.logic.V("money")))

	main.tools.close_cheat()
	await _settle(4)
	print("[作弊] 关闭：modal=%s ui_open=%s 面板可见=%s 菜单按钮可见=%s" % [
			main.tools._modal, str(main.tools.ui_open()), str(main.tools._cheat_box.visible), str(main.tools._toggle_btn.visible)])
	get_tree().quit()

## 画面上某一格文本框现在的文字
func _shown(varname: String) -> String:
	for c in main.label_root.get_children():
		if str(c.get_meta("varname", "")) == varname:
			return (c as Label).text
	return "(这一帧没有这格)"

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame
