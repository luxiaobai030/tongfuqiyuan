extends Node
## 自检：掌柜的属性页（停帧 164 / 169）上把技能挨个悬停一遍，
## 看技力 / 修为的数字会不会浮在技能说明上面。
##
## 用法：python -X utf8 tools/run_probe.py dev/attr_probe.tscn

const DIR := "res://../截图预览/属性页"

var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR))
	await _page(164)
	await _page(169)
	get_tree().quit()

func _page(frame: int) -> void:
	main._goto(frame)
	main._drain()
	await _settle(10)
	print("[属性页] ===== 第 %d 帧（停住=%s，文本框 %d 个，按钮 %d 个）====="
		% [frame, str(main.halted), main.label_root.get_child_count(), main.btn_root.get_child_count()])
	_dump("刚进来")
	await _shot("%d_刚进来" % frame)
	for bid in _buttons():
		var b := _btn(bid)
		if b == null:
			continue
		_move(b.global_position + b.size * 0.5)
		await _settle(8)
		print("[属性页] --- 悬停按钮 %d（现在帧 %d）---" % [bid, main.cur])
		_dump("悬停 %d" % bid)
		await _shot("%d_悬停_%d" % [frame, bid])
		_move(Vector2(790, 592))
		await _settle(6)
		if int(main.cur) != frame:
			print("[属性页] 悬停 %d 之后画面跳到 %d 了，跳回去重来" % [bid, main.cur])
			main._goto(frame)
			main._drain()
			await _settle(10)

func _buttons() -> Array:
	var out := []
	for c in main.btn_root.get_children():
		out.append(int(c.get_meta("id", -1)))
	return out

func _dump(tag: String) -> void:
	for c in main.label_root.get_children():
		var v := str(c.get_meta("varname", ""))
		if v == "":
			continue
		var r := Rect2((c as Control).position, (c as Control).size)
		var mark := ""
		if v == "ZG_JL" or v == "xiuwei":
			mark = "   <== 技力/修为  %s" % (c as Label).text
		print("[属性页]    %-12s %s%s" % [v, str(r), mark])
	if main.over_rect.visible:
		print("[属性页]    说明框 %s" % str(Rect2(main.over_rect.position, main.over_rect.size)))
	else:
		print("[属性页]    说明框：没有")
	for it in main._items:
		if it.get("k", "") == "et":
			continue

func _btn(id: int) -> Control:
	for c in main.btn_root.get_children():
		if int(c.get_meta("id", -1)) == id:
			return c
	return null

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	e.button_mask = 0
	Input.parse_input_event(e)

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [DIR, name])

