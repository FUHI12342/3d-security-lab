#version 330 core

// 頂点シェーダーからの入力
in vec3 v_normal;
in vec2 v_uv;
in vec3 v_world_pos;

// 出力色
out vec4 fragColor;

// ライト方向（ワールド空間）
const vec3 LIGHT_DIR = normalize(vec3(1.0, 2.0, 3.0));
const vec3 AMBIENT = vec3(0.1, 0.1, 0.15);
const vec3 DIFFUSE = vec3(1.0, 0.5, 0.0);

void main() {
    vec3 normal = normalize(v_normal);
    float diff = max(dot(normal, LIGHT_DIR), 0.0);
    vec3 color = AMBIENT + DIFFUSE * diff;
    fragColor = vec4(color, 1.0);
}
