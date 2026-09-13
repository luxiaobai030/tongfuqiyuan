extends Node
## 悬停探针：验证「鼠标移上去 / 移开」都会按原版 rollOver / rollOut 切画面
var main: Control
var hits: Array = []

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	await _wait(0.4)
	await _case(44, 183, 48, "人物页：悬停白展堂按钮")
	await _case(2171, 2231, 2172, "战斗：悬停技能按钮")
	await _case(2162, 2205, 2162, "战斗：悬停先机按钮（原版没有换帧）")
	get_tree().quit()

func _wait(sec: float) -> void:
	await get_tree().create_timer(sec).timeout

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id")) == id:
			return c
	return null

func _case(frame: int, bid: int, want: int, label: String) -> void:
	main._goto(frame)
	main._drain()
	main._render()
	await _wait(0.3)
	var b := _btn(bid)
	if b == null:
		print("[悬停] %s：第 %d 帧没有按钮 %d —— 跳过" % [label, frame, bid])
		return
	print("[悬停] %s：按钮 %d 全局矩形=%s 鼠标过滤=%d 在树中=%s" % [label, bid, str(b.get_global_rect()), b.mouse_filter, str(b.is_inside_tree())])
	b.mouse_entered.connect(func(): hits.append("enter@%d" % main.cur))
	b.mouse_exited.connect(func(): hits.append("exit@%d" % main.cur))
	_move(Vector2(5, 5))
	await _wait(0.25)
	var f0: int = main.cur
	var center: Vector2 = b.global_position + b.size * 0.5
	_move(Vector2(center.x - 6, center.y - 6))
	await _wait(0.15)
	_move(center)
	await _wait(0.5)
	var f1: int = main.cur
	var hovered = get_viewport().gui_get_hovered_control()
	print("[悬停]   移到 %s 后：帧=%d 期望=%d  viewport 当前悬停控件=%s" % [str(center), f1, want, str(hovered)])
	_move(Vector2(780, 580))
	await _wait(0.5)
	var f2: int = main.cur
	print("[悬停]   移开后：帧=%d（期望回到 %d）  信号记录=%s" % [f2, frame, str(hits)])
	hits.clear()
