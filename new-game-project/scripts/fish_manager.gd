class_name FishManager
extends Node2D

var _fish_nodes = []

func setup(screen_w: float, screen_h: float):
	for i in range(4):
		var fish = ColorRect.new()
		fish.size  = Vector2(randi_range(40, 80), randi_range(14, 22))
		fish.color = Color(0.004, 0.024, 0.106, 0.35)
		fish.position = Vector2(
			randf_range(20, screen_w - 100),
			randf_range(screen_h * 0.5, screen_h * 0.85)
		)
		fish.set_meta("speed", randf_range(25, 55))
		fish.set_meta("dir",   1.0 if randf() > 0.5 else -1.0)
		add_child(fish)
		_fish_nodes.append(fish)

func update(delta: float, screen_w: float):
	for fish in _fish_nodes:
		var speed = fish.get_meta("speed")
		var dir   = fish.get_meta("dir")
		fish.position.x += speed * dir * delta
		if fish.position.x > screen_w + 100:
			fish.set_meta("dir", -1.0)
		elif fish.position.x < -100:
			fish.set_meta("dir", 1.0)
