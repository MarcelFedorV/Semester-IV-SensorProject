extends Node2D

const ASTEROID_SCENE = preload("res://Scene/Asteroid.tscn")
var textures = [
	preload("res://Scene/BG1.png"),
	preload("res://Scene/BG2.png"),
]

const SPAWN_INTERVAL: float  = 0.55
const LANE_COUNT: int        = 6
const LANE_MIN_Y: float      = -630.0
const LANE_MAX_Y: float      =  630.0
const LANE_JITTER: float     =  40.0

@export var bg_speed: float  = 80.0

var _panels: Array           = []
var _canvas_layer: CanvasLayer
var _texture_index: int      = 1
var _viewport_h: float       = 0.0
var _viewport_w: float       = 0.0
var _chunk_w: float          = 0.0

var asteroids: Array         = []
var spawn_timer: float       = 0.0
var _last_lane: int          = -1
var player: CharacterBody2D


# ── Setup ──────────────────────────────────────────────────────────────────────

func _ready() -> void:
	player = get_tree().get_first_node_in_group("player")
	if player == null:
		push_error("LevelGenerator: could not find player!")
		return

	var vp_size = get_viewport().get_visible_rect().size
	_viewport_h = vp_size.y
	_viewport_w = vp_size.x
	_chunk_w    = _viewport_w
	_setup_background()


func _setup_background() -> void:
	_canvas_layer       = CanvasLayer.new()
	_canvas_layer.layer = -1
	add_child(_canvas_layer)

	for i in range(2):
		var panel := TextureRect.new()
		panel.texture      = textures[i % textures.size()]
		panel.stretch_mode = TextureRect.STRETCH_SCALE
		panel.size         = Vector2(_chunk_w, _viewport_h)
		panel.position     = Vector2(i * _chunk_w, 0.0)
		_canvas_layer.add_child(panel)
		_panels.append(panel)


# ── Per-frame ──────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	if player == null:
		return
	_scroll_background(delta)
	_handle_asteroid_spawning(delta)
	_handle_asteroid_despawning()


func _scroll_background(delta: float) -> void:
	for panel in _panels:
		panel.position.x -= bg_speed * delta

	_panels.sort_custom(func(a, b): return a.position.x < b.position.x)
	var left:  TextureRect = _panels[0]
	var right: TextureRect = _panels[1]

	if left.position.x + _chunk_w <= 0.0:
		_texture_index  = (_texture_index + 1) % textures.size()
		left.texture    = textures[_texture_index]
		left.position.x = right.position.x + _chunk_w


# ── Asteroids ─────────────────────────────────────────────────────────────────

func _handle_asteroid_spawning(delta: float) -> void:
	spawn_timer -= delta
	if spawn_timer <= 0.0:
		spawn_asteroid()
		spawn_timer = SPAWN_INTERVAL


func _handle_asteroid_despawning() -> void:
	for asteroid in asteroids.duplicate():
		if not is_instance_valid(asteroid) or asteroid.position.x < player.position.x - 1200.0:
			if is_instance_valid(asteroid):
				asteroid.queue_free()
			asteroids.erase(asteroid)


func _pick_lane() -> int:
	var lane = randi() % LANE_COUNT
	while lane == _last_lane:
		lane = randi() % LANE_COUNT
	_last_lane = lane
	return lane


func spawn_asteroid() -> void:
	var lane      = _pick_lane()
	var lane_step = (LANE_MAX_Y - LANE_MIN_Y) / (LANE_COUNT - 1)
	var lane_y    = LANE_MIN_Y + lane * lane_step
	var asteroid  = ASTEROID_SCENE.instantiate()
	asteroid.position = Vector2(
		player.position.x + 2000.0,
		player.position.y + lane_y + randf_range(-LANE_JITTER, LANE_JITTER)
	)
	asteroid.z_index         = 1
	asteroid.level_generator = self
	add_child(asteroid)
	asteroids.append(asteroid)
