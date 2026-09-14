extends Node
## 菜单 / 存档框 / 标题页读档木牌的自检 + 截图。
## 用法：Godot.exe --path game res://dev/ui_shot.tscn
##
## 这个探针会真的存读档，所以开跑先把三个档位的存档原样备份到 user://_probe_backup/，
## 跑完再还原（自己新建的档位文件也删掉）—— 玩家机器上原来的存档不会被改动。

const SHOT_DIR := "res://../截图预览/菜单存档"
const BACKUP := "user://_probe_backup"

var main: Control
var had: Dictionary = {}

func _ready() -> void:
	_backup()
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame

	await _title()
	await _menu()
	await _items()
	await _slots()

	_restore()
	print("[自检] 全部跑完，存档已还原")
	get_tree().quit()

# ---------------------------------------------------------------- 备份 / 还原

func _backup() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(BACKUP))
	for i in range(1, GameState.SAVE_SLOTS + 1):
		var p := GameState.slot_path(i)
		had[i] = FileAccess.file_exists(p)
		if bool(had[i]):
			DirAccess.copy_absolute(ProjectSettings.globalize_path(p),
				ProjectSettings.globalize_path(BACKUP.path_join("slot%d.json" % i)))
	print("[自检] 备份完成，原来有的档位：%s" % str(had))

func _restore() -> void:
	for i in range(1, GameState.SAVE_SLOTS + 1):
		var p := GameState.slot_path(i)
		var b := BACKUP.path_join("slot%d.json" % i)
		if bool(had.get(i, false)):
			DirAccess.copy_absolute(ProjectSettings.globalize_path(b),
				ProjectSettings.globalize_path(p))
		elif FileAccess.file_exists(p):
			# 探针自己存出来的档，删掉
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))

# ---------------------------------------------------------------- 各个界面

func _shot(name: String) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [SHOT_DIR, name])
	print("[自检] 截图 %s.png" % name)

func _settle(n: int = 6) -> void:
	for i in n:
		await get_tree().process_frame

func _move(pos: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.global_position = pos
	e.relative = Vector2(2, 2)
	Input.parse_input_event(e)

func _title() -> void:
	main._goto(4)
	main._drain()
	await _settle(10)
	var box := Rect2()
	for c in main.btn_root.get_children():
		if int(c.get_meta("id", -1)) == int(main.TITLE_LOAD_ID):
			box = c.get_global_rect()
	print("[标题页] 帧=%d 读档木牌=%s（旁边几块是 154.5x42.6，位置对得上就对了）"
		% [main.cur, str(box)])
	print("[标题页] 右上角菜单牌=%s（高 20，正好在「跳过情节」的 y=22.8 上面）"
		% str(main.tools._toggle_btn.get_global_rect()))
	await _shot("1_标题页_读档木牌")
	await _move(box.position + box.size * 0.5)
	await _settle(4)
	await _shot("1b_标题页_读档木牌_鼠标压上去")
	await _move(Vector2(20, 560))
	await _settle(3)
	# 点一下这块木牌：应该弹三档读档框
	main._on_button(main.TITLE_LOAD_ID)
	await _settle(4)
	print("[标题页] 点读档后 读档框开着=%s 标题=%s" % [str(main.tools.dlg.is_open),
		main.tools.dlg._title.text])
	print("[标题页] 读档框黑幕=%s（应该盖满 800x600）" % str(main.tools.dlg._backdrop.size))
	await _shot("2_标题页_读档框")
	main.tools.dlg.close()
	await _settle(2)

func _menu() -> void:
	main.tools.open_menu()
	await _settle(3)
	print("[菜单] 开着=%s 菜单项=%s" % [str(main.tools._modal), main.tools._menu_items.text])
	await _shot("3_右上角菜单")
	main.tools._on_menu_item("隐藏道具")
	await _settle(3)

func _items() -> void:
	print("[道具框] 开着=%s 进度=%s" % [str(main.tools.panel_open), main.tools._progress.text])
	await _shot("4_隐藏道具框")
	main.tools.close_panel()
	await _settle(2)

func _slots() -> void:
	main.tools.open_slots("save")
	await _settle(3)
	await _shot("5_存档框_空档位")
	# 往档位三存一次
	main.tools.dlg._on_slot(3)
	await _settle(3)
	print("[存档] 档位三=%s" % str(GameState.slot_info(3)))
	await _shot("6_存档框_存好了")
	# 再点一次：应该先问「覆盖？」
	main.tools.dlg._on_slot(3)
	await _settle(3)
	await _shot("7_存档框_问覆盖")
	main.tools.dlg.close()
	await _settle(2)
	# 往前走一段再读档，看画面跳不跳得回去
	var at: int = main.cur
	main._goto(at + 120)
	main._drain()
	await _settle(4)
	var msg := str(main.do_load(3))
	await _settle(4)
	print("[读档] %s 帧 %d → %d（存档时在 %d）" % [msg, at + 120, main.cur, at])
	main.tools.open_slots("load")
	await _settle(3)
	await _shot("8_读档框")
	main.tools.dlg.close()
	await _settle(2)
