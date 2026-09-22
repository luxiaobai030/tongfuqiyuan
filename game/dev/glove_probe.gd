extends Node
## 自检：第 60 天从客栈菜单点老白，一路走到买手套那一步。
## 用法：python -X utf8 tools/run_probe.tscn
var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	await _play(10000, "钱够（10000 文）")
	await _play(2000, "钱不够（2000 文）")
	get_tree().quit()

func _play(money: int, tag: String) -> void:
	print("\n[手套] ============ %s ============" % tag)
	main._goto(268)
	main._drain()
	main.logic.setv("day", 60)
	main.logic.setv("houy", 0)
	main.logic.setv("money", money)
	main.logic.setv("money_tishi", "%d文" % money)
	await _settle(8)
	print("[手套]   客栈页 帧=%d 钱=%s houy=%s" % [main.cur, str(main.logic.V("money")), str(main.logic.V("houy"))])
	await _click(_center(519))
	print("[手套]   点老白（519）后 帧=%d houy=%s" % [main.cur, str(main.logic.V("houy"))])
	var last := -1
	for step in 80:
		if int(main.cur) >= 1955:
			break
		if int(main.cur) != last:
			print("[手套]   帧 %d" % main.cur)
			last = int(main.cur)
		var bid := _hot()
		if bid == 0:
			print("[手套]   帧 %d 没有整屏热区" % main.cur)
			break
		await _click(_center(bid))
	print("[手套]   停在帧 %d，钱=%s，这一帧的按钮：%s" % [main.cur, str(main.logic.V("money")), _buttons()])
	var pay := _center(1984)
	if pay != Vector2.ZERO:
		await _click(pay)
		print("[手套]   点「给你钱！」后 帧=%d 钱=%s" % [main.cur, str(main.logic.V("money"))])
	else:
		print("[手套]   这一帧没有 1984（钱够的话已经停在 1956 成交画面上了）")
	await _settle(30)
	print("[手套]   再等一会儿        帧=%d 钱=%s halted=%s 按钮=%s" % [
			main.cur, str(main.logic.V("money")), str(main.halted), _buttons()])

func _hot() -> int:
	for it in main._items:
		if it.get("k", "") != "btn":
			continue
		var box: Array = it.get("box", [])
		if box.size() >= 4 and float(box[2]) * float(box[3]) > 800.0 * 600.0 * 0.5:
			return int(it.get("id", 0))
	return 0

func _buttons() -> String:
	var out := []
	for it in main._items:
		if it.get("k", "") == "btn":
			out.append(str(int(it.get("id", -1))))
	return ",".join(out)

func _center(bid: int) -> Vector2:
	var box: Array = main._box_of(bid)
	if box.size() < 4:
		return Vector2.ZERO
	return Vector2(float(box[0]) + float(box[2]) * 0.5, float(box[1]) + float(box[3]) * 0.5)

func _click(pos: Vector2) -> void:
	if pos == Vector2.ZERO:
		return
	_move(Vector2(2, 590))
	await _settle(2)
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
	await _settle(10)
	_move(Vector2(2, 590))
	await _settle(4)

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame
