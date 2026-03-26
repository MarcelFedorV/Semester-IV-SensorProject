extends Node2D

# ── State ────────────────────────────────
var depth       = 0.0
var is_moving   = false
var active_time = 0.0

const CATCH_INTERVAL = 45.0

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
	# Get actual screen size
	var viewport = get_viewport().get_visible_rect().size
	screen_w = viewport.x
	screen_h = viewport.y

	catch_reveal.visible = false
	status_label.text = "Press arrow keys to move"

	# Set initial line start point to dock position
	fishing_line.set_point_position(0, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT))
	fishing_line.set_point_position(1, Vector2(screen_w * CENTER_X_PCT, screen_h * DOCK_Y_PCT + 10))

func _process(delta):
	_handle_input()
	_update_depth(delta)
	_update_visuals()

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
	var target = 1.0 if is_moving else 0.0
	depth = lerp(depth, target, delta * 0.5)
	depth_bar.value = depth * 100

	if is_moving:
		active_time += delta
		status_label.text = "Moving - line going deeper"
		if active_time >= CATCH_INTERVAL:
			active_time = 0.0
			_show_catch("Fish", "THE fish.")
	else:
		status_label.text = "Stop - line rising"

# ── Visuals ──────────────────────────────
func _update_visuals():
	var center_x  = screen_w * CENTER_X_PCT
	var dock_y    = screen_h * DOCK_Y_PCT
	var max_depth = screen_h * MAX_DEPTH_Y_PCT

	var bobber_y = lerp(dock_y + 20, max_depth, depth)

	# Move bobber
	bobber.position = Vector2(center_x - bobber.size.x / 2, bobber_y)

	# Update line endpoint
	fishing_line.set_point_position(0, Vector2(center_x, dock_y))
	fishing_line.set_point_position(1, Vector2(center_x, bobber_y))

	# Water gets darker with depth
	var r = lerp(0.04, 0.02, depth)
	var g = lerp(0.22, 0.08, depth)
	var b = lerp(0.42, 0.15, depth)
	water.color = Color(r, g, b)

# ── Catch ────────────────────────────────
func _show_catch(name_text: String, fact: String):
	fish_name.text = name_text
	fish_fact.text = fact
	catch_reveal.visible = true

func _input(event):
	# Tap anywhere to dismiss catch reveal
	if catch_reveal.visible:
		if event is InputEventScreenTouch and event.pressed:
			catch_reveal.visible = false
		if event is InputEventMouseButton and event.pressed:
			catch_reveal.visible = false
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
