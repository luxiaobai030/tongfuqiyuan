extends Node
## 三个 bug 的修复自检 + 截图
var main: Control
var d := "res://../截图预览/修复"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))
	# bug2：说明框盖住的数字应该消失
	await _shot_frame(81, "无说明框时(81_说明框)")
	await _shot_frame(128, "无无双说明(128)")
	await _shot_frame(2550, "无战斗闪白(2550)")
	await _shot_frame(121, "无时光提示(121)")
	# bug3：悬停客栈属性图标应弹出说明
	await _hover(188, 446, "客栈属性_悬停市图标")
	await _hover(188, 89, "客栈属性_悬停左菜单")
	await _hover(74, 245, "秀才页_悬停写作图标")
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

func _shot_frame(f: int, name: String) -> void:
	main._goto(f)
	main._drain()
	main._render()
	await _wait(0.35)
	print("[修复] 到帧 %d（cur=%d）" % [f, main.cur])
	await _shot(name)

func _hover(frame: int, bid: int, name: String) -> void:
	main._goto(frame)
	main._drain()
	main._render()
	await _wait(0.3)
	_move(Vector2(3, 3))
	await _wait(0.2)
	var b := _btn(bid)
	if b == null:
		print("[修复] 帧 %d 没有按钮 %d" % [frame, bid])
		return
	await _move(b.global_position + b.size * 0.5)
	await _wait(0.4)
	print("[修复] 悬停 %d：帧 %d → %d  悬停态贴图=%s %s" % [bid, frame, main.cur,
		str(main.over_rect.texture != null), str(main.over_rect.position)])
	await _shot(name)
	_move(Vector2(790, 590))
	await _wait(0.3)
