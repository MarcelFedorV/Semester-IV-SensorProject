extends Area2D

const SPEED = 1200.0

func _physics_process(delta: float) -> void:
	position.x += SPEED * delta

func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("asteroid"):
		body.die(true)
		queue_free()

func _on_area_entered(area: Node2D) -> void:
	if area.is_in_group("asteroid"):
		area.die(true)
		queue_free()
