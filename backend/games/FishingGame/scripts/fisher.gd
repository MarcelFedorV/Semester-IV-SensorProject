class_name Fisher
extends Node2D

func setup(screen_w: float, screen_h: float, dock_y_pct: float, center_x_pct: float):
	pass


func _make_rect(size: Vector2, pos: Vector2, color: Color) -> ColorRect:
	var r = ColorRect.new()
	r.size     = size
	r.position = pos
	r.color    = color
	add_child(r)
	return r
