extends Node
## 开发用截图工具（不参与正式游戏）
##   Godot.exe --path . res://dev/shot.tscn            → 全部
##   Godot.exe --path . res://dev/shot.tscn -- pages   → 只截各功能页
##   Godot.exe --path . res://dev/shot.tscn -- play    → 只跑一天流程

## 截图存到工程外层，避免被打进游戏资源里
const SHOT_DIR := "res://../截图预览"

var main: Control
var trace: Array = []
var last_frame: int = -1

const PAGES := [
	[4, "p01_标题"],
	[5, "p02_难度选择"],
	[19, "p03_大堂早上"],
	[39, "p04_人物属性说明"],
	[164, "p05_佟湘玉"],
	[44, "p06_白展堂"],
	[59, "p07_郭芙蓉"],
	[74, "p08_吕秀才"],
	[94, "p09_李大嘴"],
	[119, "p10_祝无双"],
	[142, "p11_莫小贝"],
	[188, "p12_客栈属性"],
	[198, "p13_客栈属性2"],
	[228, "p14_拜神"],
	[268, "p15_出门地图"],
	[24, "p16_大堂晚上"],
	[961, "p17_淘宝"],
	[985, "p18_逛街"],
	[901, "p19_物品制作"],
	[2160, "p20_战斗"],
	[3968, "p21_结局"],
]

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))
	var mode := "all"
	for a in OS.get_cmdline_args():
		if a == "pages" or a == "play":
			mode = a
	await _wait(0.5)
	if mode == "all" or mode == "pages":
		await _pages()
	if mode == "all" or mode == "play":
		await _play()
	get_tree().quit()

func _process(_delta: float) -> void:
	if main != null and main.cur != last_frame:
		last_frame = main.cur
		trace.append(main.cur)
		if trace.size() > 250:
			trace.pop_front()

func _pages() -> void:
	for p in PAGES:
		main._goto(int(p[0]))
		main._drain()
		await _wait(0.45)
		_dump(str(p[1]))
		await _shot(str(p[1]))

func _play() -> void:
	main._goto(4)
	main._drain()
	await _wait(0.3)
	main._on_button(32)      # 开门营业
	await _wait(0.5)
	main._on_button(48)      # 江湖小虾(正常难度)
	await _wait(0.5)
	trace.clear()
	var steps := await _drive_to(24, 600)
	print("[run] 开场剧情 %d 步 → 第 %d 帧  天数=%s 钱=%s" % [steps, main.cur, str(main.logic.V("day")), str(main.logic.V("money"))])
	print("[run] 开场轨迹=" + str(trace))
	await _shot("r01_第一天晚上")
	for day in range(2, 5):
		trace.clear()
		main._on_button(128)     # 睡觉
		await _wait(1.0)
		steps = await _drive_to(19, 300)
		print("[run] 睡到第 %s 天：%d 步 → 第 %d 帧  钱=%s 威望=%s 完美=%s 和谐=%s" % [str(main.logic.V("day")), steps, main.cur, str(main.logic.V("money")), str(main.logic.V("wlww")), str(main.logic.V("wm")), str(main.logic.V("hexie"))])
		if main.cur != 19:
			print("[run] 轨迹=" + str(trace))
			return
		await _shot("r%02d_大堂" % main.logic.V("day"))
		trace.clear()
		main._on_button(92)      # 营业
		await _wait(1.0)
		steps = await _drive_to(24, 600)
		print("[run] 第 %s 天营业：%d 步 → 第 %d 帧  钱=%s 威望=%s 完美=%s" % [str(main.logic.V("day")), steps, main.cur, str(main.logic.V("money")), str(main.logic.V("wlww")), str(main.logic.V("wm"))])
		if main.cur != 24:
			print("[run] 轨迹=" + str(trace))
			return
		await _shot("r%02d_晚上" % main.logic.V("day"))

func _drive_to(target: int, max_steps: int) -> int:
	var n := 0
	while main.cur != target and n < max_steps:
		n += 1
		if main.halted:
			var ids := _button_ids()
			if main.find_key_button("space") >= 0:
				main._press_key("space")
			elif ids.size() >= 1:
				main._on_button(int(ids[0]))
			else:
				print("[run] 卡在第 %d 帧（无按钮且已停住）" % main.cur)
				break
		await _wait(0.12)
	return n

func _wait(sec: float) -> void:
	await get_tree().create_timer(sec).timeout

func _button_ids() -> Array:
	var ids: Array = []
	for c in main.btn_root.get_children():
		ids.append(int(c.get_meta("id")))
	return ids

func _dump(tag: String) -> void:
	var labels: Array = []
	for c in main.label_root.get_children():
		labels.append("%s=%s" % [str(c.get_meta("varname")), (c as Label).text])
	print("[page] %s 帧=%d 按钮=%s" % [tag, main.cur, str(_button_ids())])
	if not labels.is_empty():
		print("[page] %s 文本=%s" % [tag, " | ".join(labels)])

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [SHOT_DIR, name])
