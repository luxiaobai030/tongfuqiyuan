extends Node
## 用真实鼠标事件驱动（会触发 hover/pressed 信号），复现闪退

var main: Control
var rng := RandomNumberGenerator.new()
var steps: int = 0
var step_limit: int = 4000

func _ready() -> void:
	rng.seed = 20260913
	for a in OS.get_cmdline_args():
		if a.is_valid_int():
			step_limit = int(a)
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	_task()

func _wait(sec: float) -> void:
	await get_tree().create_timer(sec).timeout

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(1, 1)
	Input.parse_input_event(e)

func _click(pos: Vector2) -> void:
	_move(pos)
	await _wait(0.03)
	var d := InputEventMouseButton.new()
	d.button_index = MOUSE_BUTTON_LEFT
	d.pressed = true
	d.position = pos
	d.global_position = pos
	Input.parse_input_event(d)
	await _wait(0.03)
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT
	u.pressed = false
	u.position = pos
	u.global_position = pos
	Input.parse_input_event(u)
	await _wait(0.06)

func _buttons() -> Array:
	var out: Array = []
	for c in main.btn_root.get_children():
		out.append(c)
	return out

func _center(btn: Control) -> Vector2:
	return btn.global_position + btn.size * 0.5

func _sweep() -> void:
	for i in 4:
		_move(Vector2(rng.randf_range(20, 780), rng.randf_range(20, 580)))
		await _wait(0.02)

func _pick_target() -> Button:
	var btns := _buttons()
	if btns.is_empty():
		return null
	var kid: int = int(main.find_key_button("space"))
	if kid >= 0:
		for b in btns:
			if int(b.get_meta("id")) == kid:
				return b
	return btns[0]

func _task() -> void:
	main._goto(4)
	main._drain()
	await _wait(0.4)
	# 真实点击「开门营业」
	for b in _buttons():
		if int(b.get_meta("id")) == 32:
			await _click(_center(b))
			break
	await _wait(0.5)
	for b in _buttons():
		if int(b.get_meta("id")) == 48:
			await _click(_center(b))
			break
	await _wait(0.5)
	while steps < step_limit:
		steps += 1
		if not main.halted:
			await _wait(0.05)
			await _sweep()
			continue
		var tgt := _pick_target()
		if tgt == null:
			print("[!] 无按钮 帧=", main.cur)
			await _wait(0.2)
			continue
		await _click(_center(tgt))
		if steps % 50 == 0:
			print("[input] 步=%d 帧=%d 按钮数=%d" % [steps, main.cur, _buttons().size()])
	print("[input] 结束 步=%d 帧=%d" % [steps, main.cur])
	get_tree().quit()
