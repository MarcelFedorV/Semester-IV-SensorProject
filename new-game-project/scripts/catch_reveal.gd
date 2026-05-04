class_name CatchReveal
extends Control

@onready var fish_name_label = $VBoxContainer/FishName
@onready var fish_fact_label = $VBoxContainer/FishDesc
@onready var fish_sprite = $VBoxContainer/FishSprite

signal dismissed

func show_catch(fish_name_text: String, rarity: String, fact: String, sprite_path: String = ""):
	fish_name_label.text = fish_name_text
	fish_fact_label.text = "[" + rarity.to_upper() + "] " + fact
	
	if sprite_path != "":
		print("sprite_path received: ", sprite_path)
		var texture = load("res://assets/fish/" + sprite_path)
		print("texture loaded: ", texture)
		if texture:
			fish_sprite.texture = texture
			fish_sprite.visible = true
		else:
			fish_sprite.visible = false
	else:
		fish_sprite.visible = false
	
	visible = true

func _input(event):
	if not visible:
		return
	if event is InputEventScreenTouch or event is InputEventMouseButton:
		if event.pressed:
			visible = false
			dismissed.emit()
