extends Node
## 自检：1) 左侧名单点谁进哪一页（祝无双 / 莫小贝）2) 无双页第二个加点（319）加完属性还在不在
## 用法：python -X utf8 tools/run_probe.py dev/wushuang_probe.tscn

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	await _list_clicks()
	await _wushuang()
	get_tree().quit()

func _list_clicks() -> void:
	print("[无双] ===== 左侧名单：点谁去哪一页 =====")
	for bid in [151, 137, 138, 139, 140, 193, 194]:
		main._goto(164)
		main._drain()
		await _settle(8)
		var c := _center(bid)
		if c == Vector2.ZERO:
			print("[无双]   按钮 %d 不在这一帧" % bid)
			continue
		await _click(c)
		print("[无双]   点 %d（%s）之后帧=%d" % [bid, str(c), main.cur])

func _wushuang() -> void:
	print("[无双] ===== 无双页（119）两个加点 =====")
	main._goto(119)
	main._drain()
	main.logic.setv("money", 1000)
	main.logic.setv("money_tishi", "1000文")
	await _settle(8)
	_dump("刚进页面")
	for bid in [318, 319, 329, 330]:
		var c := _center(bid)
		if c == Vector2.ZERO:
			print("[无双]   按钮 %d 不在这一帧" % bid)
			continue
		_move(c)
		await _settle(8)
		_dump("悬停 %d" % bid)
		_move(Vector2(790, 20))
		await _settle(6)
		_dump("移开 %d" % bid)
	print("[无双] ===== 点第二个加点 319 =====")
	var c2 := _center(319)
	_dump("点之前")
	await _click(c2)
	_dump("点之后")
	await _settle(30)
	_dump("再等一会儿")
	print("[无双] ===== 点第一个加点 318 =====")
	main._goto(119)
	main._drain()
	main.logic.setv("money", 1000)
	await _settle(8)
	await _click(_center(318))
	_dump("点 318 之后")

func _center(bid: int) -> Vector2:
	var box: Array = main._box_of(bid)
	if box.size() < 4:
		return Vector2.ZERO
	return Vector2(float(box[0]) + float(box[2]) * 0.5, float(box[1]) + float(box[3]) * 0.5)

func _dump(tag: String) -> void:
	var out := []
	for c in main.label_root.get_children():
		var v := str(c.get_meta("varname", ""))
		if v.begins_with("WS_") or v in ["ZG_JL", "xiuwei", "money"]:
			out.append("%s=%s" % [v, (c as Label).text])
	var msg := "[无双]   %-10s 帧=%d  逻辑 money=%s aixin=%s haogan=%s cixiu=%s  界面 %s" % [
			tag, main.cur, str(main.logic.V("money")), str(main.logic.V("WS_aixin")),
			str(main.logic.V("WS_haogan")), str(main.logic.V("WS_cixiu")), " ".join(out)]
	print(msg)

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _click(pos: Vector2) -> void:
	_move(pos)
	await _settle(3)
	var d := InputEventMouseButton.new()
	d.button_index = MOUSE_BUTTON_LEFT
	d.pressed = true
	d.position = pos
	d.global_position = pos
	Input.parse_input_event(d)
	await _settle(2)
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT
	u.pressed = false
	u.position = pos
	u.global_position = pos
	Input.parse_input_event(u)
	await _settle(8)
	_move(Vector2(790, 20))
	await _settle(4)

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame
