extends Node
## 战斗里鼠标压到选项上时的样子（开发用，检查白色高亮叠加得对不对）
var main: Control
var d := "res://../截图预览/战斗白块"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))
	main._goto(2160)
	main._drain()
	for i in 6:
		if main.cur >= 2162 and main.halted:
			break
		main._tick()
		await get_tree().process_frame
	print("停帧 %d" % main.cur)
	_move(Vector2(700, 560))
	await _wait(0.4)
	await _shot("b0_没悬停")
	for bid in [2205, 2206]:
		var b := _btn(bid)
		if b == null:
			print("!! 没有按钮 %d" % bid); continue
		_move(_center(b))
		await _wait(0.5)
		print("悬停 %d  frame=%d  over_rect=%s 可见=%s" % [bid, main.cur,
			str(main.over_rect.get_global_rect()), str(main.over_rect.visible)])
		await _shot("b%d_%d悬停" % [bid, bid])
	_move(Vector2(700, 560))
	await _wait(0.3)
	# 进技能菜单
	await _click(_center(_btn(2206)))
	await _tickn(3)
	print("技能菜单 cur=%d" % main.cur)
	await _shot("b_技能菜单_没悬停")
	for bid in [2231, 2232, 2222]:
		var b := _btn(bid)
		if b == null:
			print("!! 没有按钮 %d" % bid); continue
		_move(_center(b))
		await _wait(0.5)
		print("悬停 %d  frame=%d  over_rect=%s 可见=%s" % [bid, main.cur,
			str(main.over_rect.get_global_rect()), str(main.over_rect.visible)])
		await _shot("b%d_%d悬停" % [bid, bid])
	get_tree().quit()

func _tickn(n: int) -> void:
	for i in n:
		main._tick()
		await get_tree().process_frame

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id", -1)) == id:
			return c
	return null

func _center(b: Control) -> Vector2:
	return b.global_position + b.size * 0.5

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _click(pos: Vector2) -> void:
	_move(pos)
	await _wait(0.15)
	var d2 := InputEventMouseButton.new()
	d2.button_index = MOUSE_BUTTON_LEFT
	d2.pressed = true
	d2.position = pos
	d2.global_position = pos
	Input.parse_input_event(d2)
	await _wait(0.1)
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT
	u.pressed = false
	u.position = pos
	u.global_position = pos
	Input.parse_input_event(u)
	await _wait(0.2)

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [d, name])
