class_name GameState
extends Node
enum State { FISHING, REELING, REVEALING }

var catch_interval = 15.0 
const REEL_SPEED     = 0.3
const REEL_DECAY     = 0.15
const WS_URL         = "wss://game.sensorproject.org/ws"
var state         = State.FISHING
var depth         = 0.0
var reel_progress = 0.0
var catch_timer   = 0.0
var is_moving     = false
var sensor_active = false
var _socket := WebSocketPeer.new()
var current_speed_kmh  = 0.0
var current_cadence    = 0.0
var total_distance_m   = 0.0

signal metrics_updated(speed, cadence, distance)
signal achievement_unlocked(achievement)

signal fish_caught
signal state_changed(new_state)
func _ready() -> void:
	_socket.connect_to_url(WS_URL)
func _process(_delta: float) -> void:
	_socket.poll()
	match _socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while _socket.get_available_packet_count() > 0:
				var raw := _socket.get_packet().get_string_from_utf8()
				_handle_ws_message(raw)
		WebSocketPeer.STATE_CLOSED:
			_socket = WebSocketPeer.new()
			_socket.connect_to_url(WS_URL)
func _handle_ws_message(raw: String) -> void:
	var parse_result = JSON.parse_string(raw)
	if parse_result.error != OK:
		return
	var msg: Dictionary = parse_result.result
	if typeof(msg) != TYPE_DICTIONARY:
		return
	match msg.get("type", ""):
		"sensor_state":
			sensor_active = msg.get("active", false)
		"disconnected":
			sensor_active = false
		"metrics":
			current_speed_kmh = msg.get("speed_kmh", 0.0)
			current_cadence   = msg.get("cadence_rpm", 0.0)
			total_distance_m  = msg.get("distance_m", 0.0)
			metrics_updated.emit(current_speed_kmh, current_cadence, total_distance_m)
		"achievements_unlocked":
			var achievements = msg.get("achievements", [])
			for ach in achievements:
				achievement_unlocked.emit(ach)
				
func update(delta: float):
	match state:
		State.FISHING:
			var target = 1.0 if is_moving else 0.0
			depth = lerp(depth, target, delta * 0.5)
			if is_moving:
				catch_timer += delta
				if catch_timer >= catch_interval:
					catch_timer = 0.0
					_set_state(State.REELING)
					reel_progress = 0.0
		State.REELING:
			if is_moving:
				reel_progress += REEL_SPEED * delta
			else:
				reel_progress -= REEL_DECAY * delta
			reel_progress = clamp(reel_progress, 0.0, 1.0)
			if reel_progress >= 1.0:
				_set_state(State.REVEALING)
				fish_caught.emit()
		State.REVEALING:
			pass
func reset():
	depth         = 0.0
	reel_progress = 0.0
	catch_timer   = 0.0
	_set_state(State.FISHING)
	catch_interval = randf_range(15.0, 30.0)

func get_visual_depth() -> float:
	match state:
		State.REELING:   return 1.0 - reel_progress
		State.REVEALING: return 0.0
		_:               return depth
func _set_state(new_state):
	state = new_state
	if new_state == State.FISHING:
		catch_interval = randf_range(15.0, 30.0)
	state_changed.emit(new_state)
