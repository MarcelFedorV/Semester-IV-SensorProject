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
var current_location_id = 1
var locations = []
var current_location_index = 0
var patient_id = 1

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
@onready var boat = $Boat
@onready var fish_manager = $FishManager
@onready var fish_on_label = $UI/FishOnLabel
@onready var location_label = $UI/LocationLabel
@onready var prev_button    = $UI/PrevLocation
@onready var next_button    = $UI/NextLocation
@onready var http_locations = $HTTPRequestLocations
@onready var http_user = $HTTPRequestUser

var is_touching = false
var fish_on_timer = 0.0
const FISH_ON_DURATION = 2.0


func _fetch_user_id():
	http_user.request(BASE_URL + "/api/me")
	http_user.request_completed.connect(_on_user_loaded)

func _on_user_loaded(_result, response_code, _headers, body):
	if response_code != 200:
		print("Not authenticated — redirecting")
		# Optional: open login page in browser
		OS.shell_open(BASE_URL + "/login")
		return
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var data = json.get_data()
	patient_id = int(data["id"])
	print("Logged in as user: ", data["username"], " id: ", patient_id)
	
	

func _ready():
	await get_tree().process_frame
	var vp   = get_viewport().get_visible_rect().size
	screen_w = vp.x
	screen_h = vp.y
	collection_button.pressed.connect(_on_collection_pressed)
	prev_button.pressed.connect(_on_prev_pressed)
	next_button.pressed.connect(_on_next_pressed)
	_fetch_locations()
	_setup_boat()
	_setup_background()
	_setup_ui_theme()
	_setup_location_ui()
	_fetch_user_id()
	fisher.setup(screen_w, screen_h, DOCK_Y_PCT, CENTER_X_PCT)
	fish_manager.setup(screen_w, screen_h)

	fishing_line.set_point_position(0, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT))
	fishing_line.set_point_position(1, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT + 10))
	fishing_line.width = 1.5
	fishing_line.default_color = Color(0.9, 0.85, 0.7, 0.8)  # slight yellowish transparent

	catch_reveal.visible = false
	catch_reveal.dismissed.connect(_on_catch_dismissed)
	game_state.fish_caught.connect(_on_fish_caught)
	game_state.state_changed.connect(_on_state_changed)
	http.request_completed.connect(_on_catch_response)

	status_label.text = "Tap or pedal to fish"

func _on_collection_pressed():
	get_tree().change_scene_to_file("res://scenes/collection.tscn")

func _setup_background():
	$Background.size     = Vector2(screen_w, screen_h * DOCK_Y_PCT)
	$Background.position = Vector2.ZERO

	var water_y = screen_h * DOCK_Y_PCT
	water.position = Vector2(0, water_y)
	water.size     = Vector2(screen_w, screen_h - water_y)
	bobber.size = Vector2(40, 40)  # adjust based on how big you want it

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

	if fish_on_timer > 0.0:
		fish_on_timer -= delta
		fish_on_label.modulate.a = fish_on_timer / FISH_ON_DURATION
		if fish_on_timer <= 0.0:
			fish_on_label.visible = false

func _get_is_moving() -> bool:
	return (
		Input.is_action_pressed("ui_up")    or
		Input.is_action_pressed("ui_down")  or
		Input.is_action_pressed("ui_left")  or
		Input.is_action_pressed("ui_right") or
		is_touching                          or
		game_state.sensor_active
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
			if game_state.sensor_active:
				status_label.text = "Pedalling - line going deeper" if game_state.is_moving else "Stop pedalling - line rising"
			else:
				status_label.text = "Moving - line going deeper" if game_state.is_moving else "Tap or pedal to fish"
		GameState.State.REELING:
			status_label.text = "Reeling... %.0f%%" % (game_state.reel_progress * 100)
		GameState.State.REVEALING:
			pass

func _on_fish_caught():
	# Disconnect first if already connected to avoid stacking
	if http.request_completed.is_connected(_on_catch_response):
		http.request_completed.disconnect(_on_catch_response)
	
	var depth = game_state.depth
	http.timeout = 5.0
	http.request(
		BASE_URL + "/fish/catch?depth=%.2f&patient_id=%d&location_id=%d" % [depth, patient_id, current_location_id],
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

	var sprite = fish.get("sprite", "")
	if sprite == null:
		sprite = ""
	catch_reveal.show_catch(fish["name"], fish["rarity"], fish["fact"], sprite)
	_show_notification("🐟 %s added to collection!" % fish["name"])

func _show_notification(text: String):
	notification_label.text    = text
	notification_label.visible = true
	notification_label.modulate.a = 1.0
	notification_timer = NOTIFICATION_DURATION

func _on_catch_dismissed():
	game_state.reset()
	status_label.text = "Tap or pedal to fish"

func _on_state_changed(new_state):
	if new_state == GameState.State.REELING:
		_show_fish_on()

func _input(event):
	if event is InputEventScreenTouch:
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

func _show_fish_on():
	fish_on_label.visible = true
	fish_on_label.modulate.a = 1.0
	fish_on_timer = FISH_ON_DURATION
	
	
func _setup_boat():
	var dock_y = screen_h * DOCK_Y_PCT
	var boat_w = screen_w * 0.6
	var boat_h = boat_w * 0.5  # adjust based on image ratio
	boat.size = Vector2(boat_w, boat_h)
	boat.position = Vector2(
		screen_w * CENTER_X_PCT - boat_w / 2,
		dock_y - boat_h * 0.6  # sits on waterline
	)



func _setup_button_style(button : Button):
	var wood_texture = load("res://assets/wood_button.png")

	var style = StyleBoxTexture.new()
	style.texture = wood_texture

	var style_hover = style.duplicate()
	style_hover.modulate_color = Color(1.2, 1.1, 1.0)  # slightly brighter on hover

	var style_pressed = style.duplicate()
	style_pressed.modulate_color = Color(0.8, 0.7, 0.6)  # darker when pressed

	button.add_theme_stylebox_override("normal",  style)
	button.add_theme_stylebox_override("hover",   style_hover)
	button.add_theme_stylebox_override("pressed", style_pressed)
	button.add_theme_color_override("font_color", Color(1.0, 0.95, 0.80))
	button.add_theme_font_size_override("font_size", 16)
	
func _setup_ui_theme():
	_setup_button_style(collection_button)



func _setup_location_ui():
	var btn_size = Vector2(44, 44)
	var label_h  = 44.0
	var y        = 70.0

	# Prev button — left side
	prev_button.size     = btn_size
	prev_button.position = Vector2(10, y)

	# Next button — right side
	next_button.size     = btn_size
	next_button.position = Vector2(screen_w - btn_size.x - 10, y)

	# Location label — center between buttons
	location_label.size     = Vector2(screen_w - (btn_size.x * 2) - 40, label_h)
	location_label.position = Vector2(btn_size.x + 20, y)
	location_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	location_label.vertical_alignment   = VERTICAL_ALIGNMENT_CENTER
	location_label.text = "Baltic Sea"
	
	# Apply wood style to buttons
	_setup_button_style(prev_button)
	_setup_button_style(next_button)
	
	# Apply font to label
	var font = load("res://assets/fonts/Nunito-Bold.ttf")
	location_label.add_theme_font_override("font", font)
	location_label.add_theme_color_override("font_color", Color.WHITE)
	location_label.add_theme_constant_override("outline_size", 4)
	location_label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	location_label.add_theme_font_size_override("font_size", 20)
	


func _fetch_locations():
	http_locations.request(BASE_URL + "/locations")
	http_locations.request_completed.connect(_on_locations_loaded)

func _on_locations_loaded(_result, response_code, _headers, body):
	if response_code != 200:
		print("Failed to load locations")
		return
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var data = json.get_data()
	locations = data["locations"]
	_update_location_display()

func _update_location_display():
	if locations.is_empty():
		return
	var loc = locations[current_location_index]
	current_location_id = loc["id"]
	location_label.text = loc["name"]
	
	# Update water colors from location data
	var top  = loc["water_top"]
	var deep = loc["water_deep"]
	# Store for shader — we'll update water color dynamically
	_update_water_shader(top, deep)

func _update_water_shader(top: Array, deep: Array):
	var mat = water.material as ShaderMaterial
	if mat:
		mat.set_shader_parameter("surface_color", Vector3(top[0], top[1], top[2]))
		mat.set_shader_parameter("deep_color",    Vector3(deep[0], deep[1], deep[2]))

func _on_prev_pressed():
	current_location_index = max(0, current_location_index - 1)
	_update_location_display()

func _on_next_pressed():
	current_location_index = min(locations.size() - 1, current_location_index + 1)
	_update_location_display()
	
	
	
