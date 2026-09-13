extends SceneTree
## 校验数据模型是否与原版 79 个变量对齐

const DataSchema := preload("res://scripts/data_schema.gd")

func _init() -> void:
	var v: Dictionary = DataSchema.make_initial_vars()
	print("变量总数: %d" % v.size())
	print("角色数: %d" % DataSchema.CHAR_ORDER.size())
	print("全局项: %d" % DataSchema.GLOBAL_FIELDS.size())
	print("武功数: %d" % DataSchema.SKILLS.size())
	print("战斗项: %d" % DataSchema.COMBAT_FIELDS.size())
	print("天数上限: %d" % DataSchema.TOTAL_DAYS)
	var char_fields := 0
	for p in DataSchema.CHAR_ORDER:
		char_fields += DataSchema.CHAR_FIELDS[p].size()
	print("角色属性项: %d" % char_fields)
	var keys: Array = v.keys()
	keys.sort()
	print("全部键: %s" % ", ".join(keys))
	quit(0)
