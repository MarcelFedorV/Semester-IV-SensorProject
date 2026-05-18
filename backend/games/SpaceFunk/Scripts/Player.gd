extends CharacterBody2D

const BASE_URL = "https://game.sensorproject.org"

@export var camera: Camera2D
@export var fuel_label: Label
@export var hp_label: Label
@export var score_label: Label
@export var distance_label: Label
@export var http_user: HTTPRequest
@export var http_score: HTTPRequest

const DODGE_SPEED: float            = 500.0
const FIRE_COOLDOWN: float          = 1.0
const MAX_HEALTH: int               = 3
const INVINCIBILITY_DURATION: float = 1.5
const FUEL_MAX: float               = 100.0
const FUEL_CHARGE: float            = 3.0
const FUEL_DRAIN_INTERVAL: float    = 2.0

const BULLET_SCENE = preload("res://Scene/Bullet.tscn")

var fire_timer: float          = 0.0
var health: int                = MAX_HEALTH
var invincible: bool           = false
var invincibility_timer: float = 0.0
var fuel: float                = 100.0
var fuel_drain_timer: float    = 0.0
var external_charge: float     = 0.0
var score: int                 = 0
var current_speed_kmh: float   = 0.0
var played_distance_m: float   = 0.0
var user_id: int               = -1
var _socket := WebSocketPeer.new()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

func _ready() -> void:
	if hp_label:
		hp_label.text = "HP: " + str(health)
	if score_label:
		score_label.text = "Score: 0"
	if camera:
		camera.top_level = true
		camera.global_position = Vector2(global_position.x + 700, 0)

	var ws_url: String
	if OS.has_feature("web"):
		var host = JavaScriptBridge.eval("window.location.hostname")
		ws_url = "ws://localhost:8000/ws" if host == "localhost" else "wss://game.sensorproject.org/ws"
	else:
		ws_url = "ws://localhost:8000/ws"
	_socket.connect_to_url(ws_url)
	_fetch_user_id()


func _fetch_user_id() -> void:
	if http_user:
		http_user.request(BASE_URL + "/api/me")
		http_user.request_completed.connect(_on_user_loaded)


func _on_user_loaded(_result, response_code, _headers, body) -> void:
	if response_code != 200:
		print("Not authenticated")
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if data:
		user_id = int(data["id"])
		print("Logged in as user id: ", user_id)


func _process(_delta: float) -> void:
	_poll_socket()


func _physics_process(delta: float) -> void:
	_handle_fuel(delta)

	velocity.x = 0.0
	velocity.y = 0.0

	if Input.is_action_pressed("move_up"):
		velocity.y = -DODGE_SPEED
	elif Input.is_action_pressed("move_down"):
		velocity.y = DODGE_SPEED

	fire_timer -= delta
	if Input.is_action_just_pressed("fire") and fire_timer <= 0.0:
		_fire()
		fire_timer = FIRE_COOLDOWN

	if invincible:
		invincibility_timer -= delta
		if invincibility_timer <= 0.0:
			invincible = false

	move_and_slide()

	for i in get_slide_collision_count():
		var collider = get_slide_collision(i).get_collider()
		if collider != null and collider.is_in_group("asteroid"):
			take_damage()

	_clamp_to_screen()


func _clamp_to_screen() -> void:
	position.y = clamp(position.y, -630.0, 630.0)


# ── WebSocket / BLE sensor ────────────────────────────────────────────────────

func _poll_socket() -> void:
	_socket.poll()
	match _socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while _socket.get_available_packet_count() > 0:
				_handle_ws_message(_socket.get_packet().get_string_from_utf8())
		WebSocketPeer.STATE_CLOSED:
			external_charge = 0.0


func _handle_ws_message(raw: String) -> void:
	var msg = JSON.parse_string(raw)
	if msg == null:
		return
	match msg.get("type", ""):
		"sensor_state":
			external_charge = 1.0 if msg.get("active", false) else 0.0
		"disconnected":
			external_charge = 0.0
		"metrics":
			current_speed_kmh = msg.get("speed_kmh", 0.0)


# ── Combat ────────────────────────────────────────────────────────────────────

func _fire() -> void:
	var bullet = BULLET_SCENE.instantiate()
	bullet.position = global_position + Vector2(150, 0)
	get_tree().root.add_child(bullet)


func take_damage(amount: int = 1) -> void:
	if invincible:
		return
	health -= amount
	if hp_label:
		hp_label.text = "HP: " + str(health)
	print("Player hit! Health: ", health, " / ", MAX_HEALTH)
	if health <= 0:
		_die()
		return
	invincible = true
	invincibility_timer = INVINCIBILITY_DURATION


func add_score(amount: int = 1) -> void:
	score += amount
	if score_label:
		score_label.text = "Score: " + str(score)


func _die() -> void:
	print("Player died!")
	_save_run()
	get_tree().reload_current_scene()


func _save_run() -> void:
	if user_id == -1 or not http_score:
		return
	http_score.request(
		BASE_URL + "/spacefunk/score?score=%d&distance_m=%.1f&user_id=%d" % [score, played_distance_m, user_id],
		[],
		HTTPClient.METHOD_POST
	)


# ── Fuel ──────────────────────────────────────────────────────────────────────

func _handle_fuel(delta: float) -> void:
	if external_charge == 0.0:
		fuel_drain_timer -= delta
		if fuel_drain_timer <= 0.0:
			fuel = max(0.0, fuel - 1.0)
			fuel_drain_timer = FUEL_DRAIN_INTERVAL
			if fuel <= 0.0:
				_die()
	else:
		fuel = min(FUEL_MAX, fuel + FUEL_CHARGE * delta)

	if fuel_label:
		fuel_label.text = "Fuel: " + str(int(fuel))

	if external_charge > 0.0:
		played_distance_m += (current_speed_kmh / 3.6) * delta
	if distance_label:
		distance_label.text = "Traveled: %.2f km" % (played_distance_m / 1000.0)
