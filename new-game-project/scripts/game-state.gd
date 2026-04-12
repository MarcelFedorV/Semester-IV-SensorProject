class_name GameState
extends Node

enum State { FISHING, REELING, REVEALING }

var catch_interval = 15.0 
const REEL_SPEED     = 0.3
const REEL_DECAY     = 0.15

var state         = State.FISHING
var depth         = 0.0
var reel_progress = 0.0
var catch_timer   = 0.0
var is_moving     = false

signal fish_caught
signal state_changed(new_state)

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
