extends Node

const DataSchema := preload("res://scripts/data_schema.gd")
## 全局状态单例：持有 79 个变量 + 存档
## 对应原版 Flash 里散落在 _root 上的变量表

const SAVE_PATH := "user://tongfu_save.json"
const SAVE_VERSION := 1

signal changed

var vars: Dictionary = {}
var titles: Array = []        # 已获得的称号
var flags: Dictionary = {}    # 剧情标记（七天节点 / 七大不可思议 / 套装…）
var day: int = 1
var difficulty: int = 1
var log_lines: Array = []

func _ready() -> void:
	new_game()

# ---------- 生命周期 ----------

func new_game() -> void:
	vars = DataSchema.make_initial_vars()
	titles = []
	flags = {}
	day = 1
	difficulty = 1
	log_lines = ["同福客栈，重新开张。"]
	changed.emit()

func add_log(text: String) -> void:
	log_lines.append(text)
	if log_lines.size() > 200:
		log_lines.pop_front()

# ---------- 变量读写 ----------

func get_var(key: String, fallback: int = 0) -> int:
	return int(vars.get(key, fallback))

func set_var(key: String, value: int) -> void:
	vars[key] = value
	changed.emit()

func add_var(key: String, delta: int) -> int:
	var nv: int = get_var(key) + delta
	vars[key] = nv
	changed.emit()
	return nv

func has_title(t: String) -> bool:
	return titles.has(t)

func grant_title(t: String) -> bool:
	if titles.has(t):
		return false
	titles.append(t)
	add_log("获得称号：%s" % t)
	changed.emit()
	return true

# ---------- 存档 ----------

func to_dict() -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"day": day,
		"difficulty": difficulty,
		"vars": vars,
		"titles": titles,
		"flags": flags,
		"log_lines": log_lines,
	}

func from_dict(d: Dictionary) -> void:
	day = int(d.get("day", 1))
	difficulty = int(d.get("difficulty", 1))
	titles = d.get("titles", [])
	flags = d.get("flags", {})
	log_lines = d.get("log_lines", [])
	# 用初始表补齐缺失的变量，保证旧存档也能读
	var base: Dictionary = DataSchema.make_initial_vars()
	for k in base:
		base[k] = int(d.get("vars", {}).get(k, base[k]))
	vars = base
	changed.emit()

func save_game() -> bool:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		push_error("存档失败：%s" % error_string(FileAccess.get_open_error()))
		return false
	f.store_string(JSON.stringify(to_dict(), "  "))
	f.close()
	add_log("已存档（第 %d 天）" % day)
	return true

func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)

func load_game() -> bool:
	if not has_save():
		return false
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if f == null:
		return false
	var txt := f.get_as_text()
	f.close()
	var parsed: Variant = JSON.parse_string(txt)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("存档解析失败")
		return false
	from_dict(parsed)
	add_log("已读档（第 %d 天）" % day)
	return true

func delete_save() -> void:
	if has_save():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))
