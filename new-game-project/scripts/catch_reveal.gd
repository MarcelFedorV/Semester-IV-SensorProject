class_name CatchReveal
extends Control

@onready var fish_name_label = $VBoxContainer/FishName
@onready var fish_fact_label = $VBoxContainer/FishDesc

signal dismissed

func show_catch(fish_name_text: String, rarity: String, fact: String):
	fish_name_label.text = fish_name_text
	fish_fact_label.text = "[" + rarity.to_upper() + "] " + fact
	visible = true

func _input(event):
	if not visible:
		return
	if event is InputEventScreenTouch or event is InputEventMouseButton:
		if event.pressed:
			visible = false
			dismissed.emit()
