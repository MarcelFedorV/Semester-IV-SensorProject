class_name Fisher
extends Node2D

func setup(screen_w: float, screen_h: float, dock_y_pct: float, center_x_pct: float):
	var cx     = screen_w * center_x_pct
	var dock_y = screen_h * dock_y_pct

	_make_rect(Vector2(screen_w, 4),  Vector2(0, dock_y - 10), Color(0.32, 0.18, 0.07))
	_make_rect(Vector2(screen_w, 14), Vector2(0, dock_y - 7),  Color(0.45, 0.28, 0.12))

	_make_rect(Vector2(22, 30), Vector2(cx - 11, dock_y - 37), Color(0.18, 0.38, 0.62))
	_make_rect(Vector2(18, 18), Vector2(cx - 9,  dock_y - 55), Color(0.95, 0.78, 0.60))
	_make_rect(Vector2(24, 10), Vector2(cx - 12, dock_y - 65), Color(0.22, 0.55, 0.22))
	_make_rect(Vector2(32, 4),  Vector2(cx - 16, dock_y - 59), Color(0.22, 0.55, 0.22))

	var rod = _make_rect(Vector2(5, 40), Vector2(cx + 4, dock_y - 42), Color(0.55, 0.35, 0.10))
	rod.rotation = deg_to_rad(25)

func _make_rect(size: Vector2, pos: Vector2, color: Color) -> ColorRect:
	var r = ColorRect.new()
	r.size     = size
	r.position = pos
	r.color    = color
	add_child(r)
	return r
