class_name GameState
extends Node
enum State { FISHING, REELING, REVEALING }

var catch_interval = 15.0 
const REEL_SPEED     = 0.3
const REEL_DECAY     = 0.15
const WS_URL         = "ws://localhost:8000/ws"
var state         = State.FISHING
var depth         = 0.0
var reel_progress = 0.0
var catch_timer   = 0.0
var is_moving     = false
var sensor_active = false
var _socket := WebSocketPeer.new()
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
	var msg: Dictionary = JSON.parse_string(raw)
	if msg == null:
		return
	match msg.get("type", ""):
		"sensor_state":
			sensor_active = msg.get("active", false)  # ← fixed
		"disconnected":
			sensor_active = false                      # ← fixed
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
