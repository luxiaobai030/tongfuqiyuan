extends Node
## 角色动画层自检：
##   state —— 不截图，只把“某个角色在某一主帧的播放头”打出来，核对原版行为
##   shot  —— 逐帧截图（BG + 角色层合成后的样子），用来肉眼比对原版画面
var main: Control
var shots := [2160, 2162, 2170, 2179, 2240, 2286, 2360, 2520, 2530, 2544, 2545, 2560, 600, 228, 3400]
var shot_dir := "res://../截图预览/角色动画层"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main.set_process(false)
	var mode := "state"
	for a in OS.get_cmdline_args() + OS.get_cmdline_user_args():
		if a in ["state", "shot"]:
			mode = a
	if mode == "shot":
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(shot_dir))
	await _run(mode)
	get_tree().quit()

## 逐帧推进（跳过 stop 造成的等待，只关心角色层状态）
func _advance_to(target: int) -> void:
	while main.cur < target:
		main._step_clips()
		main._enter_frame(main.cur + 1)
	main._render()
	main.clip_view.queue_redraw()

func _report(tag: String) -> void:
	var parts := []
	for d in main.clip_state:
		var it: Dictionary = main.clip_state[d]
		parts.append("d%d=%s#%d%s" % [d, str(int(it.id)), int(it.ph), "停" if it.held else ""])
	print("[%s] 主帧 %d  在场角色 %s" % [tag, main.cur, " ".join(parts)])

func _run(mode: String) -> void:
	var list := [2160, 2162, 2170, 2179, 2240, 2286, 2520, 2524, 2525, 2526, 2540, 2544, 2545, 2560, 3406, 3567,
		564, 570, 600, 700, 737, 228, 250, 260, 293, 3300, 3312]
	for a in OS.get_cmdline_user_args():
		if a.is_valid_int():
			list = [int(a)]
	list.sort()
	for f in list:
		_advance_to(int(f))
		_report("到帧")
		if f == 2162:
			# 关键：主时间轴停住（等玩家点先机/后发）时角色应该继续走
			var before := _ph(2172)
			for i in 20:
				main._step_clips()
			print("     停帧 20 步：黑衣人播放头 %d → %d（应继续往前走，不是冻住）" % [before, _ph(2172)])
			print("     主时间轴 halted=%s，cur 仍为 %d" % [str(main.halted), main.cur])
		if f == 2170:
			# 按下“攻击”（原版按键 s，按钮 2218）→ xy_zhandou 应被点名播第 52 帧起
			main.logic.run_button(2218)
			main._drain()
			print("     按攻击键后：佟湘玉播放头 %d（原版要求 52）" % _ph(2159))
		if mode == "shot":
			await get_tree().create_timer(0.2).timeout
			await RenderingServer.frame_post_draw
			var img := get_viewport().get_texture().get_image()
			img.save_png("%s/f%04d.png" % [shot_dir, main.cur])
			print("   [截图] f%04d" % main.cur)

func _ph(cid: int) -> int:
	for d in main.clip_state:
		var it: Dictionary = main.clip_state[d]
		if int(it.id) == cid:
			return int(it.ph)
	return -1
