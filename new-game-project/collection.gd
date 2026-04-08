class_name CollectionScreen
extends Control

@onready var background = $Background
@onready var back_button = $BackButton
@onready var title = $Title
@onready var grid = $ScrollContainer/Grid
@onready var http = $HTTPRequest
@onready var fish_on_label = $UI/FishOnLabel

const BASE_URL = "https://game.sensorproject.org"


var patient_id = 1
var _texture_cache: Dictionary = {}

func _get_texture(sprite_path: String) -> Texture2D:
	if sprite_path in _texture_cache:
		return _texture_cache[sprite_path]
	var texture = load("res://assets/fish/" + sprite_path)
	_texture_cache[sprite_path] = texture
	return texture

func _ready():
	await get_tree().process_frame
	_setup_layout()
	back_button.pressed.connect(_on_back_pressed)
	http.request_completed.connect(_on_collection_loaded)
	http.request("%s/fish/collection/%d" % [BASE_URL, patient_id])

func _setup_layout():
	var vp = get_viewport().get_visible_rect().size
	background.size     = vp
	background.position = Vector2.ZERO
	background.color    = Color(0.1, 0.15, 0.25)

	title.text          = "Collection"
	title.position      = Vector2(0, 40)
	title.size          = Vector2(vp.x, 50)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 28)
	title.modulate      = Color.WHITE

	back_button.text     = "← Back"
	back_button.position = Vector2(16, 40)
	back_button.size     = Vector2(100, 40)

	$ScrollContainer.position = Vector2(0, 110)
	$ScrollContainer.size     = Vector2(vp.x, vp.y - 110)

	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)

func _on_collection_loaded(_result, response_code, _headers, body):
	if response_code != 200:
		print("Failed to load collection: ", response_code)
		return

	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var data = json.get_data()
	var fish_list = data["collection"]

	_setup_grid(fish_list)

func _setup_grid(fish_list: Array):
	# Clear any existing cards
	for child in grid.get_children():
		child.queue_free()

	var vp    = get_viewport().get_visible_rect().size
	var card_w = (vp.x - 48) / 3.0
	var card_h = card_w * 1.3

	for fish in fish_list:
		var card = _make_card(fish, fish["caught"], card_w, card_h)
		grid.add_child(card)

func _add_name_label(card: ColorRect, text: String, w: float, h: float, caught: bool):
	var label = Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment   = VERTICAL_ALIGNMENT_CENTER
	label.size     = Vector2(w, h)
	label.position = Vector2.ZERO
	label.add_theme_font_size_override("font_size", 20 if caught else 36)
	label.modulate = Color.BLACK
	card.add_child(label)
	

func _make_card(fish: Dictionary, caught: bool, w: float, h: float) -> Control:
	var card = ColorRect.new()
	card.custom_minimum_size = Vector2(w, h)
	card.color = Color(fish["color"]) if caught else Color(0.2, 0.2, 0.25)

	var strip = ColorRect.new()
	strip.size     = Vector2(w, 6)
	strip.position = Vector2.ZERO
	strip.color    = _rarity_color(fish["rarity"]) if caught else Color(0.3, 0.3, 0.35)
	card.add_child(strip)

	if caught:
		# Try to show sprite if available
		var sprite_path = fish.get("sprite", "")
		if sprite_path != null and sprite_path != "":
			var texture = _get_texture(sprite_path)
			if texture:
				var img = TextureRect.new()
				img.texture        = texture
				img.stretch_mode   = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
				img.expand_mode    = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
				img.size           = Vector2(w, h - 30)
				img.position       = Vector2(0, 6)
				card.add_child(img)
			else:
				_add_name_label(card, fish["name"], w, h, true)
		else:
			_add_name_label(card, fish["name"], w, h, true)
	else:
		_add_name_label(card, "?", w, h, false)

	if caught:
		var rarity_label = Label.new()
		rarity_label.text = fish["rarity"].to_upper()
		rarity_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rarity_label.size     = Vector2(w, 24)
		rarity_label.position = Vector2(0, h - 26)
		rarity_label.add_theme_font_size_override("font_size", 11)
		rarity_label.modulate = _rarity_color(fish["rarity"])
		card.add_child(rarity_label)
	

	return card

func _rarity_color(rarity: String) -> Color:
	match rarity:
		"Common":    return Color(0.7, 0.7, 0.7)
		"Uncommon":  return Color(0.3, 0.9, 0.3)
		"Rare":      return Color(0.3, 0.5, 1.0)
		"Legendary": return Color(1.0, 0.7, 0.1)
		_:           return Color.WHITE

func _on_back_pressed():
	get_tree().change_scene_to_file("res://scenes/main.tscn")
