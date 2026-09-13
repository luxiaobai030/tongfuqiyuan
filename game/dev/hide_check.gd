extends Node
## 逐个跑到 hidden.json 里的帧，各截一张图，供离线比对
var main: Control
var d := "res://../截图预览/_隐藏自检"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))
	var hd: Dictionary = main.hidden_data
	var ks := []
	for k in hd: ks.append(int(k))
	ks.sort()
	for f in ks:
		main._goto(f)
		main._drain()
		main._render()
		await get_tree().create_timer(0.18).timeout
		if main.cur != f:
			print("[跳过] 帧 %d 被剧本带走 → %d" % [f, main.cur])
			continue
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("%s/f%04d.png" % [d, f])
	await get_tree().process_frame
	get_tree().quit()
