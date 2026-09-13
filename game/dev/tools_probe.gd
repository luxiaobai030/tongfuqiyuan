extends Node
## 道具面板 + 存档 / 读档 自检（开发用，不参与正式游戏）
var main: Control
var d := "res://../截图预览/存档道具"
var _mouse_pos := Vector2.ZERO

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))

	# 1. 画面下角常驻开关（未收集时的样子）
	main._goto(188)
	main._drain()
	main._render()
	await _wait(0.5)
	await _shot("a1_开关_客栈属性")
	main._goto(379)
	main._drain()
	main._render()
	await _wait(0.5)
	await _shot("a1b_开关_跳过情节那一帧")
	print("[道具] 开关文字=%s 位置=%s" % [main.tools._toggle.text, str(main.tools._toggle.get_global_rect())])

	# 2. 打开面板
	main.tools.open_panel()
	await _wait(0.4)
	await _shot("a2_面板_一件都没有")
	print("[道具] 面板打开=%s 进度=%s" % [str(main.tools.panel_open), main.tools._progress.text])
	for k in ["qctz_biyue", "tb_00"]:
		var c: Dictionary = main.tools._cells[k]
		print("[布局] %s 名称=（%s）%s 效果=（%s）%s" % [k, c["n"].text, str(c["n"].get_global_rect()),
			c["f"].text, str(c["f"].get_global_rect())])
	print("[布局] 面板=%s 字体=%s 兜底=%s" % [str(main.tools._box.get_global_rect()),
		str(main.panel_font), str(main.panel_font.fallbacks if main.panel_font is FontFile else "")])

	# 3. 拿道具：帧 297 闭月簪、帧 830 沉鱼项链、按钮 1288 羞花衫、帧 968 淘宝（TBWP=7 清明上河图）
	for f in [297, 830, 1317]:
		main._goto(f)
		main._drain()
	main.tools.on_button(1288)
	main.logic.setv("TBWP", 7)
	main.logic.setv("taobao", "")
	main.tools.on_frame(968)
	await _wait(0.2)
	main.tools.refresh()
	await _wait(0.4)
	print("[道具] 收集后=%d 件：闭月=%s 沉鱼=%s 落雁=%s 羞花=%s 清明上河图=%s 玉如意=%s" % [
		GameState.item_count(), str(GameState.has_item("qctz_biyue")), str(GameState.has_item("qctz_chenyu")),
		str(GameState.has_item("qctz_luoyan")), str(GameState.has_item("qctz_xiuhua")),
		str(GameState.has_item("tb_07")), str(GameState.has_item("tb_14"))])
	await _shot("a3_面板_收集了五件")

	# 4. 拿玉如意（TBWP=14 落在最后一段）
	main.logic.setv("TBWP", 15)
	main.tools.on_frame(968)
	print("[道具] TBWP=15 时应拿到玉如意：%s" % str(GameState.has_item("tb_14")))

	# 5. 存档 / 读档
	main.logic.setv("money", 43210)
	main.logic.setv("day", 9)
	main.tools.close_panel()
	await _wait(0.2)
	var m1: String = main.do_save()
	print("[存档] %s" % m1)
	main.logic.setv("money", 1)
	main.logic.setv("day", 1)
	var m2: String = main.do_load()
	print("[存档] %s → money=%s（期望 43210） day=%s（期望 9） 帧=%d 道具=%d 件" % [
		m2, str(main.logic.V("money")), str(main.logic.V("day")), main.cur, GameState.item_count()])
	await _wait(0.4)
	await _shot("a4_读档后")

	# 6. 面板开着时按键不传给游戏；Tab 能开关面板
	main._goto(2160)
	main._drain()
	main._render()
	await _wait(0.4)
	main.tools.open_panel()
	await _wait(0.3)
	var before: int = main.cur
	_key(KEY_Z)
	await _wait(0.4)
	print("[按键] 面板开着按 z：帧 %d → %d（应不变）" % [before, main.cur])
	await _shot("a5_战斗里开着面板")
	_key(KEY_TAB)
	await _wait(0.3)
	print("[按键] 按 Tab 后面板=%s（应 false）" % str(main.tools.panel_open))
	_key(KEY_TAB)
	await _wait(0.3)
	print("[按键] 再按 Tab 面板=%s（应 true）" % str(main.tools.panel_open))
	main.tools.close_panel()
	await _wait(0.3)
	await _shot("a6_战斗里关掉面板")

	# 7. 开关本身点得到吗（模拟鼠标点右上角）
	var r: Rect2 = main.tools._toggle.get_global_rect()
	await _move(r.position + r.size * 0.5)
	await _wait(0.2)
	await _click()
	await _wait(0.3)
	print("[鼠标] 点右上角开关后面板=%s（应 true）" % str(main.tools.panel_open))
	await _move(Vector2(760, 560))
	await _wait(0.2)
	await _click()
	await _wait(0.3)
	print("[鼠标] 点黑幕后面板=%s（应 false） 帧=%d" % [str(main.tools.panel_open), main.cur])
	await _shot("a7_点黑幕关掉")
	# 8. 关着面板按 F5：提示应该顶在右上角开关上
	_key(KEY_F5)
	await _wait(0.4)
	print("[提示] F5 后开关文字=%s" % main.tools._toggle.text)
	await _shot("a8_角落里按F5的提示")
	# 9. 真走一遍游戏里的淘宝流程（帧 956 那个「淘一次」按钮），看道具会不会被记下来
	main.logic.setv("money", 999999)
	main._goto(956)
	main._drain()
	main._render()
	await _wait(0.3)
	var tries := 0
	var hit := GameState.item_count()
	for i in 60:
		main._goto(956)
		main._drain()
		main._render()
		await _wait(0.1)
		tries += 1
		main._on_button(1254)
		await _wait(0.15)
		if GameState.item_count() > hit:
			hit = GameState.item_count()
			print("[淘宝] 第 %d 次淘到：%s（当前帧 %d）" % [tries, str(_owned()), main.cur])
		if hit >= 8:
			break
	print("[淘宝] 一共淘了 %d 次，集齐 %d 件" % [tries, GameState.item_count()])
	main.tools.open_panel()
	await _wait(0.4)
	await _shot("a9_淘宝淘到之后")
	# 10. 面板开着的时候存档：提示应该走在面板的状态行上（那行的字体和正文一致）
	main.tools._do_save()
	await _wait(0.4)
	print("[提示] 面板开着时状态行=%s" % main.tools._status.text)
	await _shot("a10_面板上的存档提示")
	get_tree().quit()

func _owned() -> Array:
	var out: Array = []
	for k in GameState.items:
		out.append(str(k))
	return out

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout

func _key(code: Key) -> void:
	var e := InputEventKey.new()
	e.keycode = code
	e.physical_keycode = code
	e.pressed = true
	Input.parse_input_event(e)

func _move(pos: Vector2) -> void:
	_mouse_pos = pos
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _click() -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = true
	e.position = _mouse_pos
	e.global_position = e.position
	Input.parse_input_event(e)
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT
	u.pressed = false
	u.position = _mouse_pos
	u.global_position = e.position
	Input.parse_input_event(u)

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [d, name])
