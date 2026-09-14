extends Node
## 战斗胜利结算页自检：跳到第 2545 帧截图，看提示框里的奖励数字
## 用法：Godot.exe --path game res://dev/reward_shot.tscn
const SHOT_DIR := "res://../截图预览"
var main: Control

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._goto(2545)
	main._drain()
	for i in 20:
		main._tick()
		await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/战果提示框.png" % SHOT_DIR)
	print("[战果] 帧=%d 生命=%s 修为=%s 技力=%s 铜钱=%s 武林帖=%s" % [main.cur,
		str(main.logic.V("hp")), str(main.logic.V("xiuwei")), str(main.logic.V("ZG_JL")),
		str(main.logic.V("money")), str(main.logic.V("WLT"))])
	print("[战果] 截图：%s/战果提示框.png" % SHOT_DIR)
	get_tree().quit()
