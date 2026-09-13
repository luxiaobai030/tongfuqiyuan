extends Node
## 悬停提示（rollOver 说明框）自检：真实鼠标移上去 / 移开，并截图
var main: Control
var d := "res://../截图预览/悬停"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))
	await _case(74, 267, 79, "秀才页 七侠传行")
	await _case(164, 406, 169, "掌柜页 第一行")
	get_tree().quit()

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(3, 3)
	e.button_mask = 0
	Input.parse_input_event(e)

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id")) == id:
			return c
	return null

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [d, name])

func _case(frame: int, bid: int, want: int, label: String) -> void:
	main._goto(frame)
	main._drain()
	main._render()
	await _wait(0.35)
	var b := _btn(bid)
	if b == null:
		print("[提示] %s：帧 %d 没有按钮 %d" % [label, frame, bid])
		return
	print("[提示] %s：初始帧=%d 按钮矩形=%s" % [label, main.cur, str(b.get_global_rect())])
	await _shot("h%03d_%d_之前" % [frame, bid])
	_move(Vector2(3, 3))
	await _wait(0.2)
	await _move(b.global_position + b.size * 0.5)
	await _wait(0.4)
	print("[提示]   悬停后帧=%d 期望=%d 悬停控件=%s" % [main.cur, want, str(get_viewport().gui_get_hovered_control())])
	await _shot("h%03d_%d_悬停" % [frame, bid])
	_move(Vector2(790, 590))
	await _wait(0.4)
	print("[提示]   移开后帧=%d 期望=%d" % [main.cur, frame])
	await _shot("h%03d_%d_移开" % [frame, bid])
