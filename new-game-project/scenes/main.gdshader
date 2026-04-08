shader_type canvas_item;

void fragment() {
	// UV.y goes 0.0 (top of water) to 1.0 (bottom)
	float depth = UV.y;
	
	// Surface color (lighter blue)
	vec3 surface = vec3(0.05, 0.28, 0.52);
	// Deep color (very dark blue)
	vec3 deep    = vec3(0.01, 0.05, 0.12);
	
	// Smooth gradient from surface to deep
	vec3 color = mix(surface, deep, depth);
	
	// Subtle lighter shimmer band near surface
	float shimmer = smoothstep(0.0, 0.15, depth) * (1.0 - smoothstep(0.0, 0.3, depth));
	color += vec3(0.05, 0.08, 0.1) * shimmer;
	
	COLOR = vec4(color, 1.0);
}
