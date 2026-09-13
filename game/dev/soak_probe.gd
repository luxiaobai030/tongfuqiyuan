extends Node
## 长时间试跑：连续玩若干天，记录内存/帧号，用于复现闪退

var main: Control
var steps: int = 0

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	_run()

func _wait(sec: float) -> void:
	await get_tree().create_timer(sec).timeout

func _ids() -> Array:
	var ids: Array = []
	for c in main.btn_root.get_children():
		ids.append(int(c.get_meta("id")))
	return ids

func _drive_to(target: int, max_steps: int) -> int:
	var n := 0
	while main.cur != target and n < max_steps:
		n += 1
		if main.halted:
			var ids: Array = _ids()
			if main.find_key_button("space") >= 0:
				main._press_key("space")
			elif ids.size() >= 1:
				main._on_button(int(ids[0]))
			else:
				print("[!] 无路可走 帧=", main.cur)
				break
		await _wait(0.05)
	return n

func _run() -> void:
	main._goto(4); main._drain(); await _wait(0.4)
	main._on_button(32); await _wait(0.6)
	main._on_button(48); await _wait(0.6)
	steps = await _drive_to(24, 800)
	print("[soak] 第1天 到 24 帧，步数=", steps, " 内存=%.1fMB" % (OS.get_static_memory_usage() / 1048576.0))
	for day in range(2, 11):
		main._on_button(128)      # 睡觉
		await _wait(1.0)
		steps = await _drive_to(19, 500)
		print("[soak] 第%d天早上 帧=%d 步数=%d 钱=%s 内存=%.1fMB" % [day, main.cur, steps, str(main.logic.V("money")), OS.get_static_memory_usage() / 1048576.0])
		if main.cur != 19:
			print("[soak] 没到 19 帧，中断")
			break
		main._on_button(92)       # 营业
		await _wait(1.0)
		steps = await _drive_to(24, 900)
		print("[soak] 第%d天营业 帧=%d 步数=%d 钱=%s 内存=%.1fMB" % [day, main.cur, steps, str(main.logic.V("money")), OS.get_static_memory_usage() / 1048576.0])
		if main.cur != 24:
			print("[soak] 没到 24 帧，中断")
			break
	print("[soak] 结束 内存=%.1fMB" % (OS.get_static_memory_usage() / 1048576.0))
	get_tree().quit()