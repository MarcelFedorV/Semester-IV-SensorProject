extends CharacterBody2D

const BASE_URL = "https://game.sensorproject.org"

@export var camera: Camera2D
@export var fuel_label: Label
@export var hp_label: Label
@export var score_label: Label
@export var distance_label: Label

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

var _http_user:  HTTPRequest
var _http_score: HTTPRequest

# ── Overlay ───────────────────────────────────────────────────────────────────
enum GameState { MENU, PLAYING, PAUSED, DEAD }
var game_state: GameState = GameState.MENU

var _overlay_layer:       CanvasLayer
var _overlay_title:       Label
var _overlay_body:        Label
var _overlay_btn_primary: Button
var _overlay_btn_quit:    Button


# ── Lifecycle ─────────────────────────────────────────────────────────────────

func _ready() -> void:
	_http_user = HTTPRequest.new()
	add_child(_http_user)
	_http_score = HTTPRequest.new()
	add_child(_http_score)

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
	_build_overlay()
	_show_menu()


func _fetch_user_id() -> void:
	# Try reading uid from URL param first (passed by games.html — most reliable in iframe)
	if OS.has_feature("web"):
		var uid_str = JavaScriptBridge.eval("new URLSearchParams(window.location.search).get('uid')")
		if uid_str != null and uid_str != "null" and uid_str != "":
			user_id = int(uid_str)
			print("SpaceFunk: user_id from URL = ", user_id)
			return
	# Fallback: ask the backend directly
	_http_user.request(BASE_URL + "/api/me")
	_http_user.request_completed.connect(_on_user_loaded)

func _on_user_loaded(_result, response_code, _headers, body) -> void:
	if response_code != 200:
		print("SpaceFunk: not authenticated (", response_code, ")")
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if data and data.has("id"):
		user_id = int(data["id"])
		print("SpaceFunk: logged in as user_id=", user_id)
	else:
		print("SpaceFunk: /api/me parse failed, body=", body.get_string_from_utf8())


func _process(_delta: float) -> void:
	_poll_socket()


func _physics_process(delta: float) -> void:
	if game_state != GameState.PLAYING:
		return

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


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause"):
		match game_state:
			GameState.PLAYING: _show_pause()
			GameState.PAUSED:  _hide_overlay()


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
	print("Player died! score=", score, " dist=", played_distance_m)
	_save_run()
	_show_death()


func _save_run() -> void:
	if user_id == -1:
		print("SpaceFunk: skipping save — not logged in")
		return
	var url = BASE_URL + "/spacefunk/score?score=%d&distance_m=%.1f&user_id=%d" % [score, played_distance_m, user_id]
	print("SpaceFunk: saving run → ", url)
	if OS.has_feature("web"):
		# Use native browser fetch — Godot's HTTPRequest has a broken response.abort() in web export
		JavaScriptBridge.eval("""
			fetch('%s', {method:'POST'})
			  .then(r => r.json())
			  .then(d => console.log('SpaceFunk saved:', JSON.stringify(d)))
			  .catch(e => console.error('SpaceFunk save failed:', e));
		""" % url)
	else:
		_http_score.request(url, [], HTTPClient.METHOD_POST)

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


# ── Overlay ───────────────────────────────────────────────────────────────────

func _build_overlay() -> void:
	_overlay_layer              = CanvasLayer.new()
	_overlay_layer.layer        = 10
	_overlay_layer.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(_overlay_layer)

	var bg   = ColorRect.new()
	bg.color = Color(0.0, 0.0, 0.05, 0.82)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay_layer.add_child(bg)

	var center = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.add_child(center)

	var vbox = VBoxContainer.new()
	vbox.custom_minimum_size = Vector2(520, 0)
	vbox.add_theme_constant_override("separation", 22)
	center.add_child(vbox)

	_overlay_title = Label.new()
	_overlay_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_overlay_title.add_theme_font_size_override("font_size", 52)
	_overlay_title.add_theme_color_override("font_color", Color.WHITE)
	vbox.add_child(_overlay_title)

	_overlay_body = Label.new()
	_overlay_body.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_overlay_body.add_theme_font_size_override("font_size", 17)
	_overlay_body.add_theme_color_override("font_color", Color(0.75, 0.85, 1.0))
	_overlay_body.autowrap_mode = TextServer.AUTOWRAP_WORD
	vbox.add_child(_overlay_body)

	var spacer = Control.new()
	spacer.custom_minimum_size = Vector2(0, 10)
	vbox.add_child(spacer)

	_overlay_btn_primary = Button.new()
	_overlay_btn_primary.custom_minimum_size = Vector2(220, 52)
	_overlay_btn_primary.add_theme_font_size_override("font_size", 20)
	_overlay_btn_primary.pressed.connect(_on_primary_pressed)
	vbox.add_child(_overlay_btn_primary)

	_overlay_btn_quit = Button.new()
	_overlay_btn_quit.text = "Quit"
	_overlay_btn_quit.custom_minimum_size = Vector2(220, 44)
	_overlay_btn_quit.add_theme_font_size_override("font_size", 16)
	_overlay_btn_quit.pressed.connect(_on_quit_pressed)
	_overlay_btn_quit.visible = false
	vbox.add_child(_overlay_btn_quit)


func _show_menu() -> void:
	game_state                = GameState.MENU
	_overlay_title.text       = "SPACE FUNK"
	_overlay_body.text        = (
		"Pedal to charge fuel — stop pedalling and your ship loses power!\n\n"
		+ "Arrow  buttons      Dodge asteroids\n"
		+ "Tap screen         Fire cannon\n"
		+ "Pause button           Pause\n\n"
		+ "Survive as long as you can."
	)
	_overlay_btn_primary.text = "Start"
	_overlay_btn_quit.visible = false
	_overlay_layer.visible    = true
	get_tree().paused         = true


func _show_pause() -> void:
	game_state                = GameState.PAUSED
	_overlay_title.text       = "PAUSED"
	_overlay_body.text        = "Score: %d     Distance: %.2f km" % [score, played_distance_m / 1000.0]
	_overlay_btn_primary.text = "Resume"
	_overlay_btn_quit.visible = true
	_overlay_layer.visible    = true
	get_tree().paused         = true


func _show_death() -> void:
	game_state                = GameState.DEAD
	_overlay_title.text       = "GAME OVER"
	_overlay_body.text        = "Score: %d\nDistance: %.2f km" % [score, played_distance_m / 1000.0]
	_overlay_btn_primary.text = "Respawn"
	_overlay_btn_quit.visible = true
	_overlay_layer.visible    = true
	get_tree().paused         = true


func _hide_overlay() -> void:
	game_state             = GameState.PLAYING
	_overlay_layer.visible = false
	get_tree().paused      = false


func _on_primary_pressed() -> void:
	match game_state:
		GameState.MENU, GameState.PAUSED:
			_hide_overlay()
		GameState.DEAD:
			get_tree().paused = false
			get_tree().reload_current_scene()


func _on_quit_pressed() -> void:
	_save_run()
	if OS.has_feature("web"):
		JavaScriptBridge.eval("if (window.parent && window.parent.exitGame) window.parent.exitGame();")
	else:
		get_tree().quit()
