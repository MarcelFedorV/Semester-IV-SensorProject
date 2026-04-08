extends CharacterBody2D

@export var camera: Camera2D
@export var fuel_label: Label
@export var hp_label: Label

const SCROLL_SPEED = 320.0
const DODGE_SPEED = 500.0
const FIRE_COOLDOWN = 1.0
const MAX_HEALTH: int = 3
const INVINCIBILITY_DURATION: float = 1.5
const FUEL_MAX: float = 100.0
const FUEL_CHARGE: float = 3.0
const FUEL_DRAIN_INTERVAL: float = 5.0

const BULLET_SCENE = preload("res://Scene/Bullet.tscn")

var fire_timer: float = 0.0
var health: int = MAX_HEALTH
var invincible: bool = false
var invincibility_timer: float = 0.0
var fuel: float = 100.0
var fuel_drain_timer: float = 0.0
var external_charge: float = 0.0

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

func _clamp_to_screen() -> void:
	position.y = clamp(position.y, -630.0, 630.0)

func _update_camera() -> void:
	camera.position.x = global_position.x + 600
	camera.position.y = 0

func _fire() -> void:
	var bullet = BULLET_SCENE.instantiate()
	bullet.position = global_position + Vector2(150, 0)
	get_tree().root.add_child(bullet)

func _ready() -> void:
	if hp_label:
		hp_label.text = "HP: " + str(health)

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

func _die() -> void:
	print("Player died!")
	get_tree().reload_current_scene()

func _physics_process(delta: float) -> void:
	var direction = Vector2.ZERO
	_handle_fuel(delta)

	direction.x = 1.0
	if Input.is_action_pressed("move_up"):
		direction.y = -1.0
	elif Input.is_action_pressed("move_down"):
		direction.y = 1.0

	velocity.x = SCROLL_SPEED
	velocity.y = direction.y * DODGE_SPEED

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
		var collision = get_slide_collision(i)
		var collider = collision.get_collider()
		if collider != null and collider.is_in_group("asteroid"):
			take_damage()

	_clamp_to_screen()
	_update_camera()
