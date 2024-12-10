import os
import json
import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
import glfw
from PIL import Image

class Nami2DModel:
    def __init__(self, model_path):
        """Initialize the Nami2D model viewer."""
        self.model_dir = os.path.dirname(model_path)
        
        # Load runtime model (with UV coordinates)
        runtime_model_path = os.path.join(self.model_dir, 'atlas', 'model_runtime.json')
        with open(runtime_model_path, 'r') as f:
            self.model_data = json.load(f)
            
        # Load atlas texture
        atlas_path = os.path.join(self.model_dir, 'atlas', 'character_atlas.png')
        self.atlas_texture = self.load_texture(atlas_path)
        
        self.setup_gl()
        
    def load_texture(self, path):
        """Load a texture from file."""
        image = Image.open(path).convert('RGBA')
        img_data = np.array(list(image.getdata()), np.uint8)
        
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        return texture
        
    def setup_gl(self):
        """Setup OpenGL shaders and buffers."""
        def calculate_grid_points(grid_cells):
            """Calculate number of points needed for a grid.
            Args:
                grid_cells: [width, height] in cells
            Returns:
                [points_width, points_height, total_points]
            """
            points_w = grid_cells[0] + 1
            points_h = grid_cells[1] + 1
            return [points_w, points_h, points_w * points_h]

        vertex_shader = """
        #version 330
        layout(location = 0) in vec3 position;
        layout(location = 1) in vec2 texcoord;
        out vec2 v_texcoord;
        uniform float time;
        uniform int layer;
        
        void main() {
            vec3 pos = position;
            
            // Add some simple animation based on layer
            float layer_offset = layer * 0.1;
            pos.x += sin(time + layer_offset) * 0.1;
            pos.y += cos(time + layer_offset) * 0.1;
            
            gl_Position = vec4(pos, 1.0);
            v_texcoord = texcoord;
        }
        """

        fragment_shader = """
        #version 330
        in vec2 v_texcoord;
        out vec4 fragColor;
        uniform sampler2D tex;
        
        void main() {
            fragColor = texture(tex, v_texcoord);
        }
        """
        
        # Compile shaders
        vertex = shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
        fragment = shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
        self.shader_program = shaders.compileProgram(vertex, fragment)
        
        # Create buffers for each part
        self.part_buffers = {}
        
        for part in self.model_data['parts']:
            # Calculate grid points
            grid = part['mesh']['grid']
            points_info = calculate_grid_points(grid)
            print(f"Part '{part['name']}': {grid[0]}x{grid[1]} cells needs {points_info[0]}x{points_info[1]} points ({points_info[2]} total)")
            
            # Create mesh data
            vertices = []
            indices = []
            points = part['mesh']['points']
            uv = part['uv_coords']
            
            # Generate vertices
            for y in range(grid[1] + 1):
                for x in range(grid[0] + 1):
                    # Position
                    px = points[y * (grid[0] + 1) + x][0]
                    py = points[y * (grid[0] + 1) + x][1]
                    
                    # UV coordinates
                    tx = uv['u1'] + (uv['u2'] - uv['u1']) * (x / grid[0])
                    ty = uv['v1'] + (uv['v2'] - uv['v1']) * (y / grid[1])
                    
                    vertices.extend([px, py, 0.0, tx, ty])
                    
            # Generate indices
            for y in range(grid[1]):
                for x in range(grid[0]):
                    top_left = y * (grid[0] + 1) + x
                    top_right = top_left + 1
                    bottom_left = (y + 1) * (grid[0] + 1) + x
                    bottom_right = bottom_left + 1
                    
                    indices.extend([top_left, bottom_left, bottom_right,
                                 bottom_right, top_right, top_left])
                    
            vertices = np.array(vertices, dtype=np.float32)
            indices = np.array(indices, dtype=np.uint32)
            
            # Create buffers
            vao = glGenVertexArrays(1)
            vbo = glGenBuffers(1)
            ebo = glGenBuffers(1)
            
            glBindVertexArray(vao)
            
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
            
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
            
            # Position attribute
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, None)
            glEnableVertexAttribArray(0)
            
            # Texture coord attribute
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
            glEnableVertexAttribArray(1)
            
            self.part_buffers[part['name']] = {
                'vao': vao,
                'indices_count': len(indices),
                'layer': part['layer']
            }
            
    def render(self, time):
        """Render the model."""
        glUseProgram(self.shader_program)
        glBindTexture(GL_TEXTURE_2D, self.atlas_texture)
        
        # Sort parts by layer
        sorted_parts = sorted(self.model_data['parts'], key=lambda x: x['layer'])
        
        for part in sorted_parts:
            buffers = self.part_buffers[part['name']]
            
            # Update uniforms
            glUniform1f(glGetUniformLocation(self.shader_program, "time"), time)
            glUniform1i(glGetUniformLocation(self.shader_program, "layer"), buffers['layer'])
            
            # Draw part
            glBindVertexArray(buffers['vao'])
            glDrawElements(GL_TRIANGLES, buffers['indices_count'], GL_UNSIGNED_INT, None)

def main():
    # Initialize GLFW
    if not glfw.init():
        return
        
    # Create window
    window = glfw.create_window(800, 600, "Nami2D Prototype", None, None)
    if not window:
        glfw.terminate()
        return
        
    glfw.make_context_current(window)
    
    # Enable alpha blending
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    # Create model
    model_path = os.path.join(os.path.dirname(__file__), "..", "nami2d_models", "simple_character", "model.json")
    model = Nami2DModel(model_path)
    
    # Main loop
    start_time = glfw.get_time()
    
    print("Controls:")
    print("ESC: Quit")
    
    while not glfw.window_should_close(window):
        glfw.poll_events()
        
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break
            
        # Clear screen
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        
        # Render model
        current_time = glfw.get_time() - start_time
        model.render(current_time)
        
        glfw.swap_buffers(window)
        
    glfw.terminate()

if __name__ == "__main__":
    main()
