extends Node
## 整场战斗自检：从开战打到结束，看会不会卡住、画面会不会被莫名拉回技能菜单
var main: Control
var trace: Array = []

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._goto(2160)
	main._drain()
	var waited := 0
	while main.cur < 2162 and waited < 40:
		waited += 1
		main._tick()
		await get_tree().process_frame
	print("[战斗] 开战停帧=%d 技力=%s" % [main.cur, str(main.logic.V("ZG_JL"))])
	# 后发
	await _click(2206 if _btn(2206) != null else 2205)
	print("[战斗] 选后发后 cur=%d" % main.cur)
	var steps := 0
	var stuck := 0
	while steps < 900:
		steps += 1
		if main.halted:
			var ids := _ids()
			if ids.is_empty():
				print("[战斗] 第 %d 步：停住了但画面上没有按钮，帧=%d（可能卡死）" % [steps, main.cur])
				break
			# 优先用键盘（原版技能键 z x c v b n），没有就点第一个按钮
			var key := ""
			for k in ["z", "x", "c", "v", "b", "n"]:
				if main.find_key_button(k) >= 0:
					key = k
					break
			var before: int = main.cur
			if key != "":
				main._press_key(key)
			else:
				main._on_button(int(ids[0]))
			if main.cur == before and main.halted:
				stuck += 1
				if stuck > 8:
					print("[战斗] 第 %d 步：连点 %d 次没有反应，帧=%d 按钮=%s" % [steps, stuck, main.cur, str(ids)])
					break
			else:
				stuck = 0
		main._tick()
		if main.cur == 1:
			print("[战斗] 第 %d 步：时间轴跑回第 1 帧（战斗结束/重开）" % steps)
			break
		if main.cur >= 3490:
			print("[战斗] 第 %d 步：到了胜利结算帧 %d" % [steps, main.cur])
			break
		await get_tree().process_frame
	print("[战斗] 结束：帧=%d 步数=%d 敌人HP=%s 敌攻=%s 技力=%s 信心=%s" % [main.cur, steps,
		str(main.logic.V("diren_HP")), str(main.logic.V("diren_gongji")), str(main.logic.V("ZG_JL")), str(main.logic.V("ZG_zixin"))])
	print("[战斗] 后半段走过的帧=" + str(trace.slice(maxi(0, trace.size() - 60))))
	get_tree().quit()

func _process(_d: float) -> void:
	if main != null and main.cur != (trace.back() if not trace.is_empty() else -1):
		trace.append(main.cur)
		if trace.size() > 400:
			trace.pop_front()

func _ids() -> Array:
	var a: Array = []
	for c in main.btn_root.get_children():
		a.append(int(c.get_meta("id")))
	return a

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id")) == id:
			return c
	return null

func _click(id: int) -> void:
	var b := _btn(id)
	if b == null:
		print("[战斗] 没有按钮 %d" % id)
		return
	var pos: Vector2 = b.global_position + b.size * 0.5
	var e := InputEventMouseMotion.new()
	e.position = pos; e.global_position = pos; e.relative = Vector2(2, 2); e.button_mask = 0
	Input.parse_input_event(e)
	await get_tree().process_frame
	var d := InputEventMouseButton.new()
	d.button_index = MOUSE_BUTTON_LEFT; d.pressed = true; d.position = pos; d.global_position = pos
	Input.parse_input_event(d)
	await get_tree().process_frame
	var u := InputEventMouseButton.new()
	u.button_index = MOUSE_BUTTON_LEFT; u.pressed = false; u.position = pos; u.global_position = pos
	Input.parse_input_event(u)
	await get_tree().process_frame
	await get_tree().process_frame
