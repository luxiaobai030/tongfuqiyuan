extends Node
## 纯逻辑探针：跳到战斗起点，按键推进，逐帧打印时间轴（不渲染）
const KEYS := ["a", "d", "s", "f", "q", "z", "x", "c", "v", "b", "n", "space"]

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._goto(2160)
	main._drain()
	main._render()
	print("[探针] 跳到 ", main.cur, " 停=", main.halted)
	var trace: Array = []
	for i in 400:
		if main.cur >= 2560:
			break
		if main.halted:
			main._render()
			var bid := -1
			var used := ""
			for k in KEYS:
				var b: int = main.find_key_button(k)
				if b >= 0:
					bid = b; used = k
					break
			if bid < 0:
				var ids: Array = []
				for c in main.btn_root.get_children():
					ids.append(int(c.get_meta("id")))
				if ids.is_empty():
					trace.append([main.cur, "停住且没有按钮"])
					break
				main._on_button(int(ids[0]))
				used = "btn%d" % int(ids[0])
			else:
				main._press_key(used)
			trace.append([main.cur, "停:按 " + used])
		else:
			main._tick()
			if main.cur >= 2225 and main.cur <= 2310:
				trace.append([main.cur, "bg=" + str(main._beat_for(main.cur))])
	print("=== 战斗时间轴（2225-2310）===")
	for t in trace:
		print("  帧 %s  %s" % [str(t[0]), str(t[1])])
	print("结束帧:", main.cur)
	get_tree().quit()
