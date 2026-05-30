class_name FishManager
extends Node2D

var _fish_nodes = []

func setup(screen_w: float, screen_h: float):
	for i in range(6):
		var fish = _make_fish()
		fish.position = Vector2(
			randf_range(20, screen_w - 100),
			randf_range(screen_h * 0.5, screen_h * 0.85)
		)
		fish.set_meta("speed", randf_range(25, 55))
		fish.set_meta("dir",   1.0 if randf() > 0.5 else -1.0)
		fish.scale = Vector2.ONE * randf_range(0.6, 1.4)
		add_child(fish)
		_fish_nodes.append(fish)

func _make_fish() -> Node2D:
	var fish = Node2D.new()
	var color = Color(0.02, 0.05, 0.15, 0.5)

	# Body 
	var body = Polygon2D.new()
	body.polygon = PackedVector2Array([
		Vector2(-30, 0),   # tail left
		Vector2(-18, -7),  # back top
		Vector2(0,   -9),  # mid top
		Vector2(18,  -6),  # front top
		Vector2(25,   0),  # nose
		Vector2(18,   6),  # front bottom
		Vector2(0,    9),  # mid bottom
		Vector2(-18,  7),  # back bottom
		Vector2(-30,  0),  # tail right
	])
	body.color = color
	fish.add_child(body)

	# Tail 
	var tail = Polygon2D.new()
	tail.polygon = PackedVector2Array([
		Vector2(-30,  0),
		Vector2(-45, -12),
		Vector2(-42,  0),
		Vector2(-45,  12),
	])
	tail.color = color
	fish.add_child(tail)

	# Eye 
	var eye = Polygon2D.new()
	var eye_points = PackedVector2Array()
	for j in range(8):
		var angle = j * TAU / 8
		eye_points.append(Vector2(cos(angle), sin(angle)) * 2.5 + Vector2(14, -2))
	eye.polygon = eye_points
	eye.color = Color(0.4, 0.6, 0.8, 0.4)
	fish.add_child(eye)


	return fish

func update(delta: float, screen_w: float):
	for fish in _fish_nodes:
		var speed = fish.get_meta("speed")
		var dir   = fish.get_meta("dir")
		fish.position.x += speed * dir * delta

		fish.scale.x = abs(fish.scale.x) * dir

		if fish.position.x > screen_w + 100:
			fish.set_meta("dir", -1.0)
		elif fish.position.x < -100:
			fish.set_meta("dir", 1.0)
