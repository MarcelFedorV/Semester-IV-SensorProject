extends Node2D

const CHUNK_SCENE = preload("res://Scene/chunk.tscn")
const ASTEROID_SCENE = preload("res://Scene/Asteroid.tscn")

var textures = [
	preload("res://Scene/BG1.png"),
	preload("res://Scene/BG2.png"),
]

const CHUNK_WIDTH: float = 1000.0
const CHUNK_SPAWN_AHEAD: float = 3000.0   # spawn new chunk when player is this close to the last one
const DESPAWN_DISTANCE: float = 2100.0
const SPAWN_INTERVAL: float = 0.3
const ASTEROID_SPAWN_AHEAD: float = 2000.0
const ASTEROID_DESPAWN_BEHIND: float = 900.0
const ASTEROID_ZONES: int = 5
const ZONE_HEIGHT: float = 1400.0

var texture_index: int = 0
var zone_index: int = 0
var chunks: Array = []
var asteroids: Array = []
var spawn_timer: float = 0.0
var player: CharacterBody2D

func _ready() -> void:
	player = get_tree().get_first_node_in_group("player")
	if player == null:
		push_error("Could not find player!")
		return
	# Seed a few chunks to start
	for i in range(3):
		spawn_chunk(i * CHUNK_WIDTH)

func _process(delta: float) -> void:
	if player == null:
		return
	_handle_asteroid_spawning(delta)
	_handle_asteroid_despawning()
	_handle_chunk_spawning()
	_handle_chunk_despawning()

func _handle_chunk_spawning() -> void:
	if chunks.is_empty():
		return
	# Keep spawning one at a time as player approaches the end
	while chunks[-1].position.x < player.position.x + CHUNK_SPAWN_AHEAD:
		spawn_chunk(chunks[-1].position.x + CHUNK_WIDTH)

func _handle_chunk_despawning() -> void:
	for chunk in chunks.duplicate():
		if chunk.position.x < player.position.x - DESPAWN_DISTANCE:
			chunk.queue_free()
			chunks.erase(chunk)

func _handle_asteroid_spawning(delta: float) -> void:
	spawn_timer -= delta
	if spawn_timer <= 0.0:
		spawn_asteroid()
		spawn_timer = SPAWN_INTERVAL

func _handle_asteroid_despawning() -> void:
	for asteroid in asteroids.duplicate():
		if not is_instance_valid(asteroid) or asteroid.position.x < player.position.x - ASTEROID_DESPAWN_BEHIND:
			asteroids.erase(asteroid)

func spawn_asteroid() -> void:
	var asteroid = ASTEROID_SCENE.instantiate()
	asteroid.position = Vector2(
		player.position.x + ASTEROID_SPAWN_AHEAD + randf_range(-200.0, 200.0),
		player.position.y + randf_range(-700.0, 700.0)
	)
	add_child(asteroid)
	asteroids.append(asteroid)

func spawn_chunk(x_pos: float) -> void:
	var chunk = CHUNK_SCENE.instantiate()
	chunk.position.x = x_pos
	add_child(chunk)
	chunks.append(chunk)
	chunk.get_node("TextureRect").texture = textures[texture_index]
	texture_index = (texture_index + 1) % textures.size()
