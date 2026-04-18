shader_type canvas_item;

uniform vec3 surface_color = vec3(0.05, 0.28, 0.52);
uniform vec3 deep_color    = vec3(0.01, 0.05, 0.12);

void fragment() {
	float depth = UV.y;
	vec3 color  = mix(surface_color, deep_color, depth);
	float shimmer = smoothstep(0.0, 0.15, depth) * (1.0 - smoothstep(0.0, 0.3, depth));
	color += vec3(0.05, 0.08, 0.1) * shimmer;
	COLOR = vec4(color, 1.0);
}
