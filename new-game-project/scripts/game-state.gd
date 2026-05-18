class_name GameState
extends Node
enum State { FISHING, REELING, REVEALING }

const REEL_SPEED              = 0.3
const REEL_DECAY              = 0.15
const DEPTH_SPEED_MAX_KMH     = 20.0  # speed at which bobber is at full depth (NOT USED ANYMORE)
const DEPTH_INCREASE_RATE     = 0.3   # Depth increases 30% per second while moving
const MANUAL_MOVE_SPEED_MPS   = 3.0   # fallback movement speed for clicks/touches
var _catch_distance_m: float  = 100.0  # meters between catches (randomised)
var _last_catch_distance_m: float = 0.0
const WS_URL_LOCAL        = "ws://localhost:8000/ws"
const WS_URL_PROD         = "wss://game.sensorproject.org/ws"
const RECONNECT_DELAY     = 3.0
var state             = State.FISHING
var depth             = 0.0
var reel_progress     = 0.0
var is_moving         = false
var sensor_active     = false
var played_distance_m: float = 0.0  # speed × playtime, shown in-game
var _socket := WebSocketPeer.new()
var _reconnect_timer: float = 0.0
var current_speed_kmh  = 0.0
var current_cadence    = 0.0
var total_distance_m   = 0.0

signal metrics_updated(speed, cadence, distance)
signal achievement_unlocked(achievement)

signal fish_caught
signal state_changed(new_state)
func _get_ws_url() -> String:
	if OS.has_feature("web"):
		var host = JavaScriptBridge.eval("window.location.hostname")
		return WS_URL_LOCAL if host == "localhost" else WS_URL_PROD
	return WS_URL_LOCAL

func _ready() -> void:
	_socket.connect_to_url(_get_ws_url())

func _process(delta: float) -> void:
	_socket.poll()
	match _socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while _socket.get_available_packet_count() > 0:
				var raw := _socket.get_packet().get_string_from_utf8()
				_handle_ws_message(raw)
		WebSocketPeer.STATE_CLOSED:
			sensor_active = false
			_reconnect_timer -= delta
			if _reconnect_timer <= 0.0:
				_reconnect_timer = RECONNECT_DELAY
				_socket = WebSocketPeer.new()
				_socket.connect_to_url(_get_ws_url())

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
			# Save current distance before reset to prevent loss on reconnect
			get_parent()._save_distance()
			total_distance_m = 0.0  # Reset for clean reconnect
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
	# Accumulate in-game distance from speed × time while pedalling
	if sensor_active:
		played_distance_m += (current_speed_kmh / 3.6) * delta
	elif is_moving:
		played_distance_m += MANUAL_MOVE_SPEED_MPS * delta
		total_distance_m += MANUAL_MOVE_SPEED_MPS * delta

	match state:
		State.FISHING:
			# Depth increases over time while moving (not based on speed)
			if is_moving:
				# Increase depth continuously while moving
				depth = min(depth + DEPTH_INCREASE_RATE * delta, 1.0)
			else:
				# Slowly float back up when not moving
				depth = max(depth - 0.2 * delta, 0.0)
			
			# Catch triggered by distance travelled, not time
			var dist_traveled = total_distance_m - _last_catch_distance_m
			if dist_traveled >= _catch_distance_m:
				_last_catch_distance_m = total_distance_m
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
	depth                  = 0.0
	reel_progress          = 0.0
	_last_catch_distance_m = total_distance_m
	_set_state(State.FISHING)

func get_visual_depth() -> float:
	match state:
		State.REELING:   return 1.0 - reel_progress
		State.REVEALING: return 0.0
		_:               return depth
func _set_state(new_state):
	state = new_state
	if new_state == State.FISHING:
		_catch_distance_m      = randf_range(100.0, 300.0)
		_last_catch_distance_m = total_distance_m
	state_changed.emit(new_state)
