extends Area2D

const SPEED = 400.0
var level_generator: Node = null

func _physics_process(delta: float) -> void:
	position.x -= SPEED * delta

func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("player"):
		body.take_damage()
		die(false)

func _on_area_entered(area: Area2D) -> void:
	pass  # bullet handles scoring and calls die(true) on the asteroid directly

func die(scored: bool = false) -> void:
	if scored:
		var player = get_tree().get_first_node_in_group("player")
		if player and player.has_method("add_score"):
			player.add_score(1)
	if level_generator:
		level_generator.asteroids.erase(self)
	queue_free()
