#version 330 core

// 入力頂点属性
in vec3 in_position;
in vec3 in_normal;
in vec2 in_uv;

// MVP変換マトリクス
uniform mat4 u_mvp;

// フラグメントシェーダーへの出力
out vec3 v_normal;
out vec2 v_uv;
out vec3 v_world_pos;

void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    v_normal = in_normal;
    v_uv = in_uv;
    v_world_pos = in_position;
}
