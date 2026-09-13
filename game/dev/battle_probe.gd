extends Node
## 技能菜单（2171）真实鼠标测试：悬停 → 点击，看会不会推进
var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._goto(2160)
	main._drain()
	for i in 6:
		if main.cur >= 2162 and main.halted:
			break
		main._tick()
		await get_tree().process_frame
	print("停帧 %d halted=%s 技力=%s" % [main.cur, str(main.halted), str(main.logic.V("ZG_JL"))])
	# 点「后发」走到技能菜单
	await _click(_center(_btn(2206)))
	await _tickn(3)
	print("→ cur=%d halted=%s" % [main.cur, str(main.halted)])
	_dump()
	for sid in [2231, 2241, 2237]:
		var b := _btn(sid)
		if b == null:
			print("!! %d 不在场" % sid); continue
		print("--- 试技能 %d" % sid)
		await _move(_center(b))
		await _tickn(2)
		print("    悬停后 cur=%d" % main.cur)
		await _click(_center(_btn(sid) if _btn(sid) != null else b))
		await _tickn(3)
		print("    点击后 cur=%d halted=%s 技力=%s" % [main.cur, str(main.halted), str(main.logic.V("ZG_JL"))])
		if main.cur != 2171 and main.cur != 2172:
			break
	get_tree().quit()

func _tickn(n: int) -> void:
	for i in n:
		main._tick()
		await get_tree().process_frame

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id")) == id:
			return c
	return null

func _dump() -> void:
	var parts := []
	for c in main.btn_root.get_children():
		parts.append("%d@%s" % [int(c.get_meta("id")), str(c.get_rect().position)])
	print("   在场按钮: ", " | ".join(parts))

func _center(b: Control) -> Vector2:
	return b.global_position + b.size * 0.5

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(1, 1)
	Input.parse_input_event(e)
	await get_tree().process_frame
	await get_tree().process_frame

func _click(pos: Vector2) -> void:
	await _move(pos)
	var d := InputEventMouseButton.new()
	d.button_index = MOUSE_BUTTON_LEFT
	d.pressed = true
	d.position = pos
	d.global_position = pos
	Input.parse_input_event(d)
	await get_tree().process_frame
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT
	u.pressed = false
	u.position = pos
	u.global_position = pos
	Input.parse_input_event(u)
	await get_tree().process_frame
	await get_tree().process_frame
