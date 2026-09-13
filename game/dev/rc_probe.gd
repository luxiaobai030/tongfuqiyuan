extends Node
## 发布版自检：音乐分类 + 用真实鼠标事件玩一段时间，检查会不会崩/卡

var main: Control
var rng := RandomNumberGenerator.new()
var steps: int = 0
var target_i: int = 0

func _ready() -> void:
	rng.seed = 7
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

func _btns() -> Array:
	var out: Array = []
	for c in main.btn_root.get_children():
		out.append(c)
	return out

func _check_music() -> void:
	print("[rc] === 声音分类 ===")
	var n_music := 0
	for sid in main.sound_files:
		var f: String = str(main.sound_files[sid].get("file", ""))
		var st = load("res://assets/sfx/" + f)
		var dur := -1.0
		if st != null:
			dur = st.get_length()
		var is_music: bool = dur >= 20.0
		if is_music:
			n_music += 1
		if dur >= 6.0 or dur < 0.0:
			print("[rc]   %-26s %6.1fs  %s" % [f, dur, "音乐" if is_music else "音效"])
	print("[rc] 音乐数量=%d" % n_music)
	# 直接验证播放路径
	main._goto(354)
	main._drain()
	await _wait(0.4)
	print("[rc] 帧=%d 音乐播放中=%s 时长=%.1fs 路径=%s" % [main.cur, str(main._music.playing),
		(main._music.stream.get_length() if main._music.stream != null else -1.0), main._music_path])
	main._goto(2160)
	main._drain()
	await _wait(0.4)
	print("[rc] 帧=%d 音乐播放中=%s 时长=%.1fs 路径=%s" % [main.cur, str(main._music.playing),
		(main._music.stream.get_length() if main._music.stream != null else -1.0), main._music_path])
	# 同一首重复触发不应重启（拿当前正在播的那一首再点一次）
	main._goto(354)
	main._drain()
	await _wait(0.6)
	var path0: String = main._music_path
	var pos0: float = main._music.get_playback_position()
	var sid := path0.get_file().get_basename().split("_")[0]
	main._play_sound(sid)
	await _wait(0.4)
	print("[rc] 同一首(%s)重复触发：位置 %.2f → %.2f（应继续往前走，不归零）" % [sid, pos0, main._music.get_playback_position()])

func _task() -> void:
	await _check_music()
	await _check_anim()
	main._goto(4)
	main._drain()
	await _wait(0.4)
	print("[rc] 开始用鼠标玩：帧=%d" % main.cur)
	var last_frame := -1
	var tries := 0
	while steps < 2500:
		steps += 1
		if main.cur != last_frame:
			last_frame = main.cur
			tries = 0
			target_i = 0
		if not main.halted:
			_move(Vector2(rng.randf_range(10, 790), rng.randf_range(10, 590)))
			await _wait(0.03)
			continue
		var btns := _btns()
		if btns.is_empty():
			await _wait(0.1)
			continue
		tries += 1
		if tries > 4:
			target_i += 1
			tries = 0
			main._press_key("space")
		if target_i >= btns.size():
			target_i = 0
		var b: Control = btns[mini(target_i, btns.size() - 1)]
		await _click(b.global_position + b.size * 0.5)
		if steps % 100 == 0:
			print("[rc] 步=%d 帧=%d 按钮=%d" % [steps, main.cur, btns.size()])
	print("[rc] === 结束：步=%d 帧=%d 天数=%s 钱=%s ====" % [steps, main.cur, str(main.logic.V("day")), str(main.logic.V("money"))])
	get_tree().quit()

func _check_anim() -> void:
	print("[rc] === 战斗动画检查 ===")
	var seen := {}
	var frames := [2236, 2240, 2250, 2260, 2270, 2282, 2290]
	for f in frames:
		main._goto(int(f))
		main._drain()
		main._render()
		var p := "无"
		if main.bg_rect.texture != null:
			p = main.bg_rect.texture.resource_path.get_file()
		seen[p] = true
		print("[rc]   帧 %d → 画面 %s" % [int(f), p])
	print("[rc] 这段动画出现 %d 张不同画面（应为 %d 张）" % [seen.size(), frames.size()])
