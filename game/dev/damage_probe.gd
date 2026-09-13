extends Node
## 伤害飘字 + 战斗奖励翻倍 自检（开发用）
var main: Control
var d := "res://../截图预览/飘字"

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(d))
	await _wait(0.3)
	# 1. 战斗胜利的奖励是不是原版的两倍
	main._goto(24)
	main._drain()
	await _wait(0.2)
	var keys := ["hp", "xiuwei", "ZG_JL", "WLT", "money"]
	main.logic.setv("hp_linshi", 100)
	var before := {}
	for k in keys:
		before[k] = main.logic.V(k)
	main._goto(2545)
	main._drain()
	await _wait(0.2)
	var got := {}
	for k in keys:
		got[k] = main.logic.V(k)
	print("[结算] 战前 %s" % str(before))
	print("[结算] 战后 %s（期望 生命=106 修为+10 技力+20 威望+2 钱+100）" % str(got))
	# 2. 伤害飘字
	main._goto(24)
	main._drain()
	await _wait(0.3)
	print("[飘字] 城镇帧：飘字=%d 个（应为 0）" % main.float_root.get_child_count())
	main._goto(2162)
	main._drain()
	await _wait(0.3)
	print("[飘字] 进战斗：飘字=%d 个（应为 0）  敌人生命=%s" % [main.float_root.get_child_count(), str(main.logic.V("diren_HP"))])
	main.logic.setv("diren_HP", 100)
	main.logic.setv("hp", 100)
	await _wait(0.2)
	print("[飘字] 开场设满血：飘字=%d 个（应为 0）" % main.float_root.get_child_count())
	main.logic.setv("diren_HP", 63)
	main.logic.setv("hp", 91)
	await _wait(0.18)
	print("[飘字] 敌人挨 37 / 自己挨 9：文字=%s（期望 -37、-9）" % str(_texts()))
	await _shot("飘字")
	await _wait(1.4)
	print("[飘字] 1.4 秒后：飘字=%d 个（应为 0）" % main.float_root.get_child_count())
	main.logic.setv("hp", 120)
	await _wait(0.18)
	print("[飘字] 回血 29：文字=%s（期望 +29 绿字）" % str(_texts()))
	await _shot("飘字_回血")
	# 3. 敌人被回血不该飘
	await _wait(1.4)
	main.logic.setv("diren_HP", 100)
	await _wait(0.18)
	print("[飘字] 敌人回血：飘字=%d 个（应为 0）" % main.float_root.get_child_count())
	get_tree().quit()

func _texts() -> Array:
	var out := []
	for c in main.float_root.get_children():
		out.append((c as Label).text)
	return out

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [d, name])

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout
