extends Node2D

const BASE_URL = "https://game.sensorproject.org"

const DOCK_Y_PCT    = 0.25
const MAX_DEPTH_PCT = 0.85
const CENTER_X_PCT  = 0.5

var screen_w = 390.0
var screen_h = 844.0
var notification_timer = 0.0
const NOTIFICATION_DURATION = 3.0
var tap_timer   = 0.0
const TAP_PULSE = 0.5

@onready var bobber       = $Bobber
@onready var fishing_line = $Line
@onready var water        = $WaterSurface
@onready var depth_bar    = $UI/DepthBar
@onready var status_label = $UI/StatusLabel
@onready var catch_reveal = $UI/CatchReveal
@onready var collection_button    = $UI/CollectionButton
@onready var notification_label   = $UI/NotificationLabel
@onready var http = $HTTPRequest
@onready var game_state   = $GameState
@onready var fisher       = $Fisher
@onready var fish_manager = $FishManager

var is_touching = false

func _ready():
	await get_tree().process_frame
	var vp   = get_viewport().get_visible_rect().size
	screen_w = vp.x
	screen_h = vp.y
	collection_button.pressed.connect(_on_collection_pressed)

	_setup_background()
	fisher.setup(screen_w, screen_h, DOCK_Y_PCT, CENTER_X_PCT)
	fish_manager.setup(screen_w, screen_h)

	fishing_line.set_point_position(0, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT))
	fishing_line.set_point_position(1, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT + 10))

	catch_reveal.visible = false
	catch_reveal.dismissed.connect(_on_catch_dismissed)
	game_state.fish_caught.connect(_on_fish_caught)
	game_state.state_changed.connect(_on_state_changed)

	status_label.text = "Press arrow keys to move"
	
func _on_collection_pressed():
	get_tree().change_scene_to_file("res://scenes/collection.tscn")

func _setup_background():
	$Background.position = Vector2(0, 0)
	$Background.size     = Vector2(screen_w, screen_h)
	$Background.color    = Color(0.868, 0.88, 0.955, 1.0)

	var water_y = screen_h * DOCK_Y_PCT
	water.position = Vector2(0, water_y)
	water.size     = Vector2(screen_w, screen_h - water_y)

func _process(delta):
	game_state.is_moving = _get_is_moving()
	game_state.update(delta)
	fish_manager.update(delta, screen_w)
	_update_visuals()
	_update_status_label()
	if notification_timer > 0.0:
		notification_timer -= delta
		notification_label.modulate.a = notification_timer / NOTIFICATION_DURATION
		if notification_timer <= 0.0:
			notification_label.visible = false

func _get_is_moving() -> bool:
	return (
		Input.is_action_pressed("ui_up")    or
		Input.is_action_pressed("ui_down")  or
		Input.is_action_pressed("ui_left")  or
		Input.is_action_pressed("ui_right") or
		is_touching
	)

func _update_visuals():
	var cx        = screen_w * CENTER_X_PCT
	var dock_y    = screen_h * DOCK_Y_PCT
	var max_depth = screen_h * MAX_DEPTH_PCT
	var vd        = game_state.get_visual_depth()

	var bobber_y = lerp(dock_y + 20, max_depth, vd)
	bobber.position = Vector2(cx - bobber.size.x / 2, bobber_y)
	fishing_line.set_point_position(0, Vector2(cx, dock_y))
	fishing_line.set_point_position(1, Vector2(cx, bobber_y))

	water.color = Color(
		lerp(0.04, 0.02, vd),
		lerp(0.22, 0.08, vd),
		lerp(0.42, 0.15, vd)
	)

	depth_bar.value = (
		game_state.reel_progress * 100
		if game_state.state == GameState.State.REELING
		else game_state.depth * 100
	)

func _update_status_label():
	match game_state.state:
		GameState.State.FISHING:
			status_label.text = "Moving - line going deeper" if game_state.is_moving else "Stop - line rising"
		GameState.State.REELING:
			status_label.text = "Reeling... %.0f%%" % (game_state.reel_progress * 100)
		GameState.State.REVEALING:
			pass

func _on_fish_caught():
	var depth = game_state.depth
	http.request(
		BASE_URL + "/fish/catch?depth=%.2f&patient_id=1" % depth,
		[],
		HTTPClient.METHOD_POST
	)
	http.request_completed.connect(_on_catch_response)

func _on_catch_response(_result, response_code, _headers, body):
	http.request_completed.disconnect(_on_catch_response)
	if response_code != 200:
		print("Catch request failed: ", response_code)
		return

	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var data = json.get_data()
	var fish = data["fish"]

	catch_reveal.show_catch(fish["name"], fish["rarity"], fish["fact"])
	_show_notification("%s added to collection!" % fish["name"])

func _show_notification(text: String):
	notification_label.text    = text
	notification_label.visible = true
	notification_label.modulate.a = 1.0
	notification_timer = NOTIFICATION_DURATION

func _on_catch_dismissed():
	game_state.reset()
	status_label.text = "Press arrow keys to move"

func _on_state_changed(new_state):
	if new_state == GameState.State.REELING:
		status_label.text = "Fish on! Keep moving to reel it in!"

func _input(event):
	if event is InputEventScreenTouch:
		# don't trigger fishing if touch is on a Control node (like a button)
		if event.pressed:
			var clicked = get_viewport().gui_get_focus_owner()
			if clicked == null:
				tap_timer   = TAP_PULSE
				is_touching = true
		else:
			is_touching = false

	if event is InputEventMouseButton:
		if event.pressed:
			if not collection_button.get_rect().has_point(event.position):
				tap_timer   = TAP_PULSE
				is_touching = true
		else:
			is_touching = false

func _notification(what):
	if what == NOTIFICATION_WM_SIZE_CHANGED:
		var vp   = get_viewport().get_visible_rect().size
		screen_w = vp.x
		screen_h = vp.y
