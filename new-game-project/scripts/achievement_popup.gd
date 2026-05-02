class_name AchievementPopup
extends PanelContainer

@onready var icon_label  = $AchievementBox/AchievementIcon
@onready var title_label = $AchievementBox/VBoxContainer/AchievementTitle
@onready var desc_label  = $AchievementBox/VBoxContainer/AchievementDesc

var _queue: Array = []
var _showing = false
var _timer   = 0.0
const SHOW_DURATION = 4.0

var _target_y  = 20.0
var _hidden_y  = -200.0
var _current_y = -200.0

func _ready():
	position.y = _hidden_y
	visible    = true

func show_achievement(achievement: Dictionary):
	_queue.append(achievement)
	if not _showing:
		_show_next()

func _show_next():
	if _queue.is_empty():
		_showing = false
		return
	_showing = true
	var ach = _queue.pop_front()
	icon_label.text  = ach.get("icon", "🏆")
	title_label.text = ach.get("name", "Achievement!")
	desc_label.text  = ach.get("description", "")
	_current_y = _hidden_y
	_timer     = SHOW_DURATION

func _process(delta):
	if not _showing:
		return
	_timer -= delta
	if _timer > SHOW_DURATION - 0.5:
		_current_y = lerp(_current_y, _target_y, delta * 8.0)
	elif _timer < 0.5:
		_current_y = lerp(_current_y, _hidden_y, delta * 8.0)
		if _timer <= 0.0:
			_show_next()
	position.y = _current_y
