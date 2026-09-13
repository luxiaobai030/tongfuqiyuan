extends Node
## 逐帧截图探针：把战斗动画的一段帧逐张截下来，验证画面确实在变
const FRAMES := [2236, 2238, 2240, 2244, 2248, 2252, 2256, 2260, 2264, 2270, 2276, 2282, 2290, 2294, 2295, 2300]
var main: Control
var shot_dir := "res://../截图预览/战斗动画"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(shot_dir))
	await _run()

func _run() -> void:
	for f in FRAMES:
		main._goto(int(f))
		main._drain()
		main._render()
		await get_tree().create_timer(0.25).timeout
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png("%s/f%04d.png" % [shot_dir, int(f)])
		var bgp := "无"
		if main.bg_rect.texture != null:
			bgp = main.bg_rect.texture.resource_path.get_file()
		var txp := "无"
		if main.clip_view != null:
			txp = "角色层 %d 个" % main.clip_state.size()
		print("[截图] 帧 %d 背景=%s 文字=%s 当前帧=%d" % [int(f), bgp, txp, main.cur])
	get_tree().quit()
