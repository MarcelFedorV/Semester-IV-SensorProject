extends Node2D

# ── State ────────────────────────────────
var depth       = 0.0
var is_moving   = false
var active_time = 0.0
enum State {FISHING, REELING, REVEALING}
var state = State.FISHING
var reel_progress = 0.0
var catch_timer = 0.0
const CATCH_INTERVAL = 10.0
const REEL_SPEED = 0.3
const REEL_DECAY = 0.15


# Screen size — set in _ready
var screen_w = 390.0
var screen_h = 844.0

# Proportional positions
const DOCK_Y_PCT      = 0.25
const MAX_DEPTH_Y_PCT = 0.85
const CENTER_X_PCT    = 0.5

# ── Node refs ────────────────────────────
@onready var bobber       = $Bobber
@onready var fishing_line = $Line
@onready var depth_bar    = $UI/DepthBar
@onready var status_label = $UI/StatusLabel
@onready var catch_reveal = $UI/CatchReveal
@onready var fish_name    = $UI/CatchReveal/VBoxContainer/FishName
@onready var fish_fact    = $UI/CatchReveal/VBoxContainer/FishDesc
@onready var water        = $WaterSurface

var is_touching = false

func _ready():
	catch_reveal.visible = false
	status_label.text = "Press arrow keys to move"
	# Wait one frame for viewport to be fully initialized
	await get_tree().process_frame
	_setup_layout()
	_setup_silhouette_fish()

func _setup_layout():
	var viewport = get_viewport().get_visible_rect().size
	screen_w = viewport.x
	screen_h = viewport.y
	
	# Fix background
	$Background.position = Vector2(0, 0)
	$Background.size = Vector2(screen_w, screen_h)
	$Background.color = Color(0.868, 0.88, 0.955, 1.0)
	
	# Fix water
	var water_start_y = screen_h * DOCK_Y_PCT
	water.position = Vector2(0, water_start_y)
	water.size = Vector2(screen_w, screen_h - water_start_y)
	
	# Set line start
	fishing_line.set_point_position(0, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT))
	fishing_line.set_point_position(1, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT + 10))
	
	
func _process(delta):
	_handle_input()
	_update_depth(delta)
	_update_visuals()
	_update_silhouette_fish(delta)

# ── Input ────────────────────────────────
func _handle_input():
	is_moving = (
		Input.is_action_pressed("ui_up")    or
		Input.is_action_pressed("ui_down")  or
		Input.is_action_pressed("ui_left")  or
		Input.is_action_pressed("ui_right") or
		is_touching
	)

# ── Depth ────────────────────────────────
func _update_depth(delta):
	match state:
		State.FISHING:
			var target = 1.0 if is_moving else 0.0
			depth = lerp(depth, target, delta * 0.5)
			depth_bar.value = depth * 100

			if is_moving:
				catch_timer += delta
				status_label.text = "Moving - line going deeper"
				if catch_timer >= CATCH_INTERVAL:
					catch_timer = 0.0
					state = State.REELING
					reel_progress = 0.0
					status_label.text = "Fish on! Keep moving to reel it in!"
			else:
				status_label.text = "Stop - line rising"

		State.REELING:
			if is_moving:
				reel_progress += REEL_SPEED * delta
			else:
				reel_progress -= REEL_DECAY * delta
			reel_progress = clamp(reel_progress, 0.0, 1.0)
			depth_bar.value = reel_progress * 100
			status_label.text = "Reeling... %.0f%%" % (reel_progress * 100)

			if reel_progress >= 1.0:
				state = State.REVEALING
				_show_catch("THE Fish", "Legendary", "Fish")

		State.REVEALING:
			pass

# ── Visuals ──────────────────────────────
func _update_visuals():
	var center_x  = screen_w * CENTER_X_PCT
	var dock_y    = screen_h * DOCK_Y_PCT
	var max_depth = screen_h * MAX_DEPTH_Y_PCT

	var visual_depth = depth
	match state:
		State.REELING:
			visual_depth = 1.0 - reel_progress
		State.REVEALING:
			visual_depth = 0.0

	var bobber_y = lerp(dock_y + 20, max_depth, visual_depth)
	bobber.position = Vector2(center_x - bobber.size.x / 2, bobber_y)
	fishing_line.set_point_position(0, Vector2(center_x, dock_y))
	fishing_line.set_point_position(1, Vector2(center_x, bobber_y))

	var r = lerp(0.04, 0.02, visual_depth)
	var g = lerp(0.22, 0.08, visual_depth)
	var b = lerp(0.42, 0.15, visual_depth)
	water.color = Color(r, g, b)

# ── Catch ────────────────────────────────
func _show_catch(fish_name_text: String, rarity: String, fact: String):
	fish_name.text = fish_name_text
	fish_fact.text = "[" + rarity.to_upper() + "] " + fact
	catch_reveal.visible = true

func _on_catch_dismissed():
	catch_reveal.visible = false
	state = State.FISHING
	reel_progress = 0.0
	depth = 0.0
	catch_timer = 0.0
	status_label.text = "Press arrow keys to move"

func _input(event):
	# Tap anywhere to dismiss catch reveal
	if catch_reveal.visible:
		if event is InputEventScreenTouch or event is InputEventMouseButton:
			if event.pressed:
				_on_catch_dismissed()
	return

	# Track touch state
	if event is InputEventScreenTouch:
		is_touching = event.pressed

	if event is InputEventMouseButton:
		is_touching = event.pressed

# ── Screen resize ────────────────────────
func _notification(what):
	if what == NOTIFICATION_WM_SIZE_CHANGED:
		var viewport = get_viewport().get_visible_rect().size
		screen_w = viewport.x
		screen_h = viewport.y
		
		
		
		
		# ── Silhouette fish ──────────────────────────────────────────────────
var fish_nodes = []

func _setup_silhouette_fish():
	for i in range(4):
		var fish = ColorRect.new()
		fish.size = Vector2(randi_range(40, 80), randi_range(14, 22))
		fish.color = Color(0.004, 0.024, 0.106, 0.35)
		fish.position = Vector2(
			randf_range(20, screen_w - 100),
			randf_range(screen_h * 0.5, screen_h * 0.85)
		)
		fish.set_meta("speed", randf_range(25, 55))
		fish.set_meta("dir", 1.0 if randf() > 0.5 else -1.0)
		add_child(fish)
		fish_nodes.append(fish)

func _update_silhouette_fish(delta):
	for fish in fish_nodes:
		var speed = fish.get_meta("speed")
		var dir   = fish.get_meta("dir")
		fish.position.x += speed * dir * delta
		if fish.position.x > screen_w + 100:
			fish.set_meta("dir", -1.0)
		elif fish.position.x < -100:
			fish.set_meta("dir", 1.0)
