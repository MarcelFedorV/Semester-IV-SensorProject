class_name CollectionScreen
extends Control

const BASE_URL = "https://game.sensorproject.org"

@onready var background  = $Background
@onready var back_button = $BackButton
@onready var title       = $Title
@onready var scroll      = $ScrollContainer
@onready var vbox        = $ScrollContainer/VBox
@onready var http        = $HTTPRequest
@onready var tab_scroll = $TabScroll
@onready var tab_bar    = $TabScroll/TabBar

var patient_id = 1
var RARITIES   = ["Common", "Uncommon", "Rare", "Legendary"]
var current_tab = "All"
var tab_locations = [] 

var drag_start = Vector2.ZERO
var is_dragging = false

func _input(event):
	if event is InputEventScreenTouch:
		if event.pressed:
			drag_start  = event.position
			is_dragging = true
		else:
			is_dragging = false
	
	if event is InputEventScreenDrag and is_dragging:
		var delta = event.position - drag_start
		drag_start = event.position
		scroll.scroll_vertical -= int(delta.y)

func _ready():
	await get_tree().process_frame
	_setup_layout()
	_setup_button_style(back_button)
	back_button.pressed.connect(_on_back_pressed)
	http.request_completed.connect(_on_collection_loaded)
	http.request("%s/fish/collection/%d" % [BASE_URL, patient_id])

func _setup_layout():
	scroll.get_v_scroll_bar().custom_minimum_size.x = 0
	var vp = get_viewport().get_visible_rect().size
	background.size     = vp
	background.position = Vector2.ZERO
	background.color    = Color(0.1, 0.15, 0.25)

	title.text         = "🐟 Collection"
	title.position     = Vector2(0, 40)
	title.size         = Vector2(vp.x, 50)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 28)
	title.modulate     = Color.WHITE

	back_button.text     = "← Back"
	back_button.position = Vector2(16, 40)
	back_button.size     = Vector2(100, 40)

	tab_scroll.position = Vector2(0, 95)
	tab_scroll.size     = Vector2(vp.x, 50)

	scroll.position = Vector2(0, 150)
	scroll.size     = Vector2(vp.x, vp.y - 150)

func _on_collection_loaded(_result, response_code, _headers, body):
	if response_code != 200:
		print("Failed to load collection: ", response_code)
		return
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var data      = json.get_data()
	var fish_list = data["collection"]
	var mystery   = data["mystery_fish"]
	
	print("mystery data: ", mystery)  

	if tab_bar.get_child_count() == 0:
		_setup_tabs(fish_list)

	var filtered = fish_list
	var filtered_mystery = []  

	if current_tab == "All":
		filtered = fish_list
	else:
		filtered = fish_list.filter(func(f): return f.get("location", "") == current_tab)
		filtered_mystery = mystery.filter(func(m): return m.get("location", "") == current_tab)

	await _build_collection(filtered, filtered_mystery)

func _build_collection(fish_list: Array, mystery_list: Array):
	for child in vbox.get_children():
		child.queue_free()
	await get_tree().process_frame

	var vp     = get_viewport().get_visible_rect().size
	var card_w = (vp.x - 48) / 3.0
	var card_h = card_w * 1.3

	# Group fish by rarity
	var grouped = {}
	for r in RARITIES:
		grouped[r] = []
	for fish in fish_list:
		var r = fish["rarity"]
		if grouped.has(r):
			grouped[r].append(fish)

	# Build rarity sections
	for rarity in RARITIES:
		var fish_in_rarity = grouped[rarity]
		if fish_in_rarity.is_empty():
			continue

		var header = Label.new()
		header.text    = rarity.to_upper()
		header.modulate = _rarity_color(rarity)
		header.add_theme_font_size_override("font_size", 18)
		header.custom_minimum_size = Vector2(0, 36)
		vbox.add_child(header)

		var hbox = HBoxContainer.new()
		var count = 0
		for fish in fish_in_rarity:
			if count % 3 == 0:
				hbox = HBoxContainer.new()
				hbox.add_theme_constant_override("separation", 12)
				vbox.add_child(hbox)
			var card = _make_card(fish, fish["caught"], card_w, card_h)
			hbox.add_child(card)
			count += 1

		var spacer = Control.new()
		spacer.custom_minimum_size = Vector2(0, 16)
		vbox.add_child(spacer)

	var any_unlocked = mystery_list.any(func(m): return not m.get("locked", false))
	if not any_unlocked:
		return
	
	
	var mystery_header = Label.new()
	mystery_header.text    = "✨ LOCATION LEGENDS"
	mystery_header.modulate = Color(1.0, 0.85, 0.0)
	mystery_header.add_theme_font_size_override("font_size", 18)
	mystery_header.custom_minimum_size = Vector2(0, 36)
	vbox.add_child(mystery_header)

	var mystery_hbox = HBoxContainer.new()
	mystery_hbox.add_theme_constant_override("separation", 12)
	vbox.add_child(mystery_hbox)

	for mystery in mystery_list:
		var locked = mystery.get("locked", false)
		var card   = _make_card(mystery, mystery.get("caught", false), card_w, card_h, locked)
		mystery_hbox.add_child(card)

func _make_card(fish: Dictionary, caught: bool, w: float, h: float, locked: bool = false) -> Control:
	var card = ColorRect.new()
	card.custom_minimum_size = Vector2(w, h)

	if locked:
		card.color = Color(0.15, 0.10, 0.25)
	elif caught:
		card.color = Color(fish["color"])
	else:
		card.color = Color(0.2, 0.2, 0.25)

	var strip = ColorRect.new()
	strip.size     = Vector2(w, 6)
	strip.position = Vector2.ZERO
	if locked:
		strip.color = Color(0.4, 0.4, 0.4)
	elif fish["rarity"] == "Location Legend":
		strip.color = Color(1.0, 0.85, 0.0)
	else:
		strip.color = _rarity_color(fish["rarity"]) if caught else Color(0.3, 0.3, 0.35)
	card.add_child(strip)

	if locked:
		_add_label(card, "🔒", w, h, false)
	elif caught:
		var sprite_path = fish.get("sprite", "")
		if sprite_path != null and sprite_path != "":
			var texture = load("res://assets/fish/" + sprite_path)
			if texture:
				var img = TextureRect.new()
				img.texture      = texture
				img.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
				img.expand_mode  = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
				img.size         = Vector2(w, h - 30)
				img.position     = Vector2(0, 6)
				card.add_child(img)
			else:
				_add_label(card, fish["name"], w, h, true)
		else:
			_add_label(card, fish["name"], w, h, true)
	else:
		var placeholder = "???" if fish["rarity"] == "Location Legend" else "?"
		_add_label(card, placeholder, w, h, false)

	var name_label = Label.new()
	name_label.text = fish["name"] if (caught and not locked) else "???"
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.size     = Vector2(w, 24)
	name_label.position = Vector2(0, h - 26)
	name_label.add_theme_font_size_override("font_size", 11)
	name_label.modulate = Color(1.0, 0.85, 0.0) if fish["rarity"] == "Location Legend" else Color.BLACK
	card.add_child(name_label)  # ← was missing!

	return card  # ← was missing!

func _add_label(card: ColorRect, text: String, w: float, h: float, caught: bool) -> void:
	var label = Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment   = VERTICAL_ALIGNMENT_CENTER
	label.size     = Vector2(w, h)
	label.position = Vector2.ZERO
	label.add_theme_font_size_override("font_size", 20 if caught else 36)
	label.modulate = Color.BLACK
	card.add_child(label)

func _rarity_color(rarity: String) -> Color:
	match rarity:
		"Common":    return Color(0.7, 0.7, 0.7)
		"Uncommon":  return Color(0.3, 0.9, 0.3)
		"Rare":      return Color(0.3, 0.5, 1.0)
		"Legendary": return Color(1.0, 0.7, 0.1)
		_:           return Color.WHITE

func _on_back_pressed():
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _setup_button_style(button: Button):
	var wood_texture = load("res://assets/wood_button.png")
	var style = StyleBoxTexture.new()
	style.texture = wood_texture
	var style_hover = style.duplicate()
	style_hover.modulate_color = Color(1.2, 1.1, 1.0)
	var style_pressed = style.duplicate()
	style_pressed.modulate_color = Color(0.8, 0.7, 0.6)
	button.add_theme_stylebox_override("normal",  style)
	button.add_theme_stylebox_override("hover",   style_hover)
	button.add_theme_stylebox_override("pressed", style_pressed)
	button.add_theme_color_override("font_color", Color(1.0, 0.95, 0.80))
	button.add_theme_font_size_override("font_size", 16)




func _setup_tabs(fish_list: Array):
	# Clear existing tabs
	for child in tab_bar.get_children():
		child.queue_free()

	# Get unique locations from fish list
	var seen = []
	tab_locations = ["All"]
	for fish in fish_list:
		var loc = fish.get("location", "")
		if loc != "" and loc not in seen:
			seen.append(loc)
			tab_locations.append(loc)

	# Create tab buttons
	for tab in tab_locations:
		var btn = Button.new()
		btn.text = tab
		btn.custom_minimum_size = Vector2(80, 40)
		_setup_button_style(btn)
		btn.pressed.connect(_on_tab_pressed.bind(tab))
		tab_bar.add_child(btn)

func _on_tab_pressed(tab: String):
	current_tab = tab
	http.request("%s/fish/collection/%d" % [BASE_URL, patient_id])
