extends Node
## 自检：属性页那一行「技力 / 修为」什么时候该露着、什么时候该被说明框盖住。
## 用法：python -X utf8 tools/run_probe.py dev/hide_shot.tscn

const DIR := "res://../截图预览/数字遮挡"
const WATCH := ["ZG_JL", "xiuwei", "WS_haogan"]

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR))
	for f in [164, 169, 170, 45, 46, 79, 125, 119, 141, 148]:
		main._goto(f)
		main._drain()
		await get_tree().create_timer(0.25).timeout
		print("[数字] 帧 %-4d %s" % [f, _line()])
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("%s/%d.png" % [DIR, f])
	get_tree().quit()

func _line() -> String:
	var out := []
	for c in main.label_root.get_children():
		var v := str(c.get_meta("varname", ""))
		if WATCH.has(v):
			out.append("%s=%s" % [v, (c as Label).text])
	return " ".join(out) if out else "（一个都没画）"
