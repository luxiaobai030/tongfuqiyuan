extends Node
## 自检：点剧情的时候画面还会不会闪白。
##
## 两件事分开验：
##   1. 直接读按钮的样式对象 —— 真按钮的 hover / pressed 该是白色高亮，
##      整屏热区（占画面 >25%）该是空的 StyleBoxEmpty。
##   2. 画面验证 —— 把时间轴冻住（不冻的话剧情一直在走，亮度本来就在变，量不准），
##      按住整屏热区，再手动把那层白加回去，同一个画面下比一次。
##
## 用法：python -X utf8 tools/run_probe.py dev/story_probe.tscn

const DIR := "res://../截图预览/白块检查"
const STORY_FRAME := 1100

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR))

	main._goto(4)
	main._drain()
	await _settle(14)
	_report("标题页的小木牌按钮", _worst_btn())

	main._goto(STORY_FRAME)
	main._drain()
	await _settle(14)
	var b := _worst_btn()
	_report("剧情帧的整屏热区", b)
	if b == null:
		get_tree().quit()
		return
	var bid := int(b.get_meta("id", -1))
	var c := b.global_position + b.size * 0.5

	await _freeze(6)
	_move(Vector2(1, 598))
	await _freeze(5)
	var before := await _shot_mean("剧情_没压鼠标")
	_move(c)
	await _freeze(5)
	var hover := await _shot_mean("剧情_鼠标压上去")
	_hold(c, true)
	await _freeze(5)
	var down := await _shot_mean("剧情_按住")

	# 对照：把原来那层白手动加回去（同一个画面、同一帧），看它当年白成什么样
	var bb := _btn(bid)
	if bb != null:
		bb.add_theme_stylebox_override("pressed", main._hover_style(0.20))
		bb.queue_redraw()
	await _freeze(5)
	var white := await _shot_mean("剧情_按住且把那层白加回去")

	_hold(c, false)
	await _freeze(4)
	print("\n[剧情] 画面平均亮度（0-255，越高越白）")
	print("[剧情]   没压鼠标                  %.1f" % before)
	print("[剧情]   鼠标压上去                %.1f" % hover)
	print("[剧情]   按住（修好之后）          %.1f" % down)
	print("[剧情]   按住（把那层白加回去）    %.1f   <- 改之前就是这个样子" % white)
	print("[剧情]   两个差 %.1f（差越大，改之前点剧情白得越狠）" % (white - down))
	get_tree().quit()

## 冻住时间轴：不冻的话剧情一直在走，画面本来就在变，亮度没法比
func _freeze(n: int) -> void:
	main.halted = true
	main.pending = 0
	await _settle(n)
	main.halted = true
	main.pending = 0

func _report(tag: String, b: Control) -> void:
	if b == null:
		print("[白块] %s：没找到" % tag)
		return
	var r := Rect2(b.global_position, b.size)
	print("[白块] %s id=%d  %s  占画面 %.0f%%"
		% [tag, int(b.get_meta("id", -1)), str(r), r.get_area() / (800.0 * 600.0) * 100.0])
	for st in ["hover", "pressed"]:
		var sb := b.get_theme_stylebox(st)
		var extra := ""
		if sb is StyleBoxFlat:
			extra = "  底色调 = %s" % str((sb as StyleBoxFlat).bg_color)
		print("[白块]     %-8s → %s%s" % [st, sb.get_class(), extra])

func _worst_btn() -> Control:
	var best: Control = null
	var area := 0.0
	for c in main.btn_root.get_children():
		if int(c.get_meta("id", -1)) == int(main.TITLE_LOAD_ID):
			continue
		var a: float = c.size.x * c.size.y
		if a > area:
			area = a
			best = c
	return best

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id", -1)) == id:
			return c
	return null

func _shot_mean(name: String) -> float:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [DIR, name])
	return _mean(img)

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _hold(pos: Vector2, down: bool) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = down
	e.position = pos
	e.global_position = pos
	Input.parse_input_event(e)

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func _mean(img: Image) -> float:
	var sum := 0.0
	var n := 0
	for y in range(0, img.get_height(), 4):
		for x in range(0, img.get_width(), 4):
			var p := img.get_pixel(x, y)
			sum += (p.r + p.g + p.b) / 3.0
			n += 1
	return sum / maxf(1.0, float(n)) * 255.0

