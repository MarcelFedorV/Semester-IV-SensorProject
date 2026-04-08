extends Area2D

const SPEED = 400.0
var level_generator: Node

func _physics_process(delta: float) -> void:
	position.x -= SPEED * delta

func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("player"):
		body.take_damage()
		die()
	elif body.is_in_group("bullet"):
		die()

func die() -> void:
	if level_generator:
		level_generator.asteroids.erase(self)
	queue_free()
