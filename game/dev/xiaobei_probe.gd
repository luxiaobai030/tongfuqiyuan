extends Node
## 自检：小贝页「允许」那两个按钮（书院后山探险 / 西凉河摸鱼）点不点得动。
## 数值照抄玩家存档：学习150 童心50 钱1984 没外出 白天 time0=0、xxbb=1（存档停在第142帧）
## 用法：python -X utf8 tools/run_probe.py dev/xiaobei_probe.tscn

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	_watchdog()
	await _run()
	get_tree().quit()

func _watchdog() -> void:
	await get_tree().create_timer(40.0).timeout
	print("[小贝] 超时了，强退")
	get_tree().quit()

func _run() -> void:
	_seed()
	_state("玩家存档那套数值")

	print("[小贝] ==== 名单页点莫小贝：白天进 141，晚上才进 142")
	for t in [0, 1]:
		main.logic.setv("time0", t)
		main._goto(39)
		main._drain()
		await _settle(8)
		await _click_at(Vector2(138, 448))
		print("[小贝]   time0=%d 名单页（按钮142）→ 帧=%d" % [t, main.cur])
		main._goto(44)
		main._drain()
		await _settle(8)
		await _click_at(Vector2(138, 448))
		print("[小贝]   time0=%d 人物页（按钮194）→ 帧=%d" % [t, main.cur])

	print("[小贝] ==== 白天条件不够：点下去要说一句为什么")
	main.logic.setv("time0", 0)
	for f in [141, 142]:
		main._goto(f)
		main._drain()
		await _settle(8)
		print("[小贝]   第 %d 帧的允许按钮：%s" % [f, _slots()])
		await _click_at(Vector2(720, 372))
		print("[小贝]     点上 → 帧=%d 提示=%s" % [main.cur, _tips()])
		main.logic.setv("waichu", 0)
		main._goto(f)
		main._drain()
		await _settle(6)
		await _click_at(Vector2(720, 418))
		print("[小贝]     点下 → 帧=%d 提示=%s" % [main.cur, _tips()])
		main.logic.setv("waichu", 0)

	print("[小贝] ==== 真晚上（time0=1）：拦住并说明")
	main.logic.setv("time0", 1)
	main.logic.setv("XB_tongxin", 100)
	main._goto(142)
	main._drain()
	await _settle(8)
	await _click_at(Vector2(720, 372))
	print("[小贝]   点上 → 帧=%d 提示=%s" % [main.cur, _tips()])

	print("[小贝] ==== 条件够了（学习150 童心100 钱1984 白天）：该真的出门")
	main.logic.setv("time0", 0)
	main.logic.setv("XB_xuexi", 150)
	main.logic.setv("XB_tongxin", 100)
	main.logic.setv("money", 1984)
	main.logic.setv("money_tishi", "1984文")
	main.logic.setv("waichu", 0)
	main._goto(141)
	main._drain()
	await _settle(8)
	await _click_at(Vector2(720, 372))
	_state("点后山（条件够了）")
	main.logic.setv("waichu", 0)
	main.logic.setv("XB_xuexi", 150)
	main.logic.setv("XB_tongxin", 100)
	main._goto(142)
	main._drain()
	await _settle(8)
	await _click_at(Vector2(720, 418))
	_state("点摸鱼（条件够了）")

func _seed() -> void:
	main.logic.setv("day", 11)
	main.logic.setv("day_tishi", "11天")
	main.logic.setv("xxbb", 1)
	main.logic.setv("time0", 0)
	main.logic.setv("money", 1984)
	main.logic.setv("money_tishi", "1984文")
	main.logic.setv("XB_chenghao", "小丫头片子")
	main.logic.setv("XB_xuexi", 150)
	main.logic.setv("XB_tongxin", 50)
	main.logic.setv("XB_haogan", 100)
	main.logic.setv("XB_wan", 0)
	main.logic.setv("waichu", 0)

func _state(tag: String) -> void:
	print("[小贝]   %-14s 帧=%d 学习=%s 童心=%s 好感=%s 钱=%s 外出=%s time0=%s xxbb=%s 提示=%s" % [
		tag, main.cur, str(main.logic.V("XB_xuexi")), str(main.logic.V("XB_tongxin")),
		str(main.logic.V("XB_haogan")), str(main.logic.V("money")), str(main.logic.V("waichu")),
		str(main.logic.V("time0")), str(main.logic.V("xxbb")), _tips()])

func _slots() -> String:
	var out := []
	for c in main.btn_root.get_children():
		var p: Vector2 = (c as Control).position
		if p.x > 690.0:
			out.append("%d@%.0f,%.0f" % [int(c.get_meta("id", -1)), p.x, p.y])
	return " ".join(out)

func _tips() -> String:
	var out := []
	for c in main.float_root.get_children():
		if c is Label:
			out.append((c as Label).text)
	return " / ".join(out) if out.size() > 0 else "（没有）"

func _click_at(pos: Vector2) -> void:
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
	await _settle(6)
	_move(Vector2(400, 560))
	await _settle(3)

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
