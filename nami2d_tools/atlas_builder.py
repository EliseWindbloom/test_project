import os
import yaml
import zipfile
import tempfile
from PIL import Image
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union

class YAMLGenerator:
    def __init__(self, indent_spaces: int = 2):
        """
        Initialize YAML generator with configurable indentation.
        
        :param indent_spaces: Number of spaces to use for indentation
        """
        self.indent_spaces = indent_spaces
    
    def _format_value(self, value: Any) -> str:
        """
        Format different types of values appropriately for YAML.
        
        :param value: Value to be formatted
        :return: Formatted string representation
        """
        if isinstance(value, str):
            return value
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return self._format_list(value)
        else:
            return str(value)
    
    def _format_list(self, lst: List[Any]) -> str:
        """
        Format a list with special attention to coordinate lists.
        
        :param lst: List to be formatted
        :return: Formatted list string
        """
        # Simple lists like grid (no decimal places)
        if len(lst) <= 4 and all(isinstance(x, int) for x in lst):
            return f"[{', '.join(str(x) for x in lst)}]"
        
        # Special handling for position list (preserve original decimal precision)
        if len(lst) >= 1 and len(lst) <= 4 and all(isinstance(x, (int, float)) for x in lst):
            return f"[{', '.join(f'{x:.1f}' if x == int(x) else str(x) for x in lst)}]"
        
        # Special handling for mesh points
        if len(lst) > 6 and all(isinstance(x, (int, float)) for x in lst):
            return self._format_mesh_points(lst)
        
        # Special handling for children (no extra spaces)
        if len(lst) > 0 and all(isinstance(x, str) for x in lst):
            return f"[{', '.join(x for x in lst)}]"
        
        # Default list formatting
        return f"[ {', '.join(self._format_value(x) for x in lst)} ]"
    
    def _format_mesh_points(self, points: List[float]) -> str:
        """
        Format mesh points with specific multi-line formatting matching test.yaml.
        
        :param points: List of point coordinates
        :return: Formatted points list string
        """
        # Group points into sets of 2
        formatted_rows = []
        row_size = 3  # 3 points per row
        
        for i in range(0, len(points), row_size * 2):
            row_points = points[i:i + row_size * 2]
            formatted_row = []
            
            for j in range(0, len(row_points), 2):
                # Format each coordinate pair
                x, y = row_points[j], row_points[j+1]
                formatted_row.append(f"[{x:g}, {y:g}]")
            
            formatted_rows.append("" + ", ".join(formatted_row))
        
        return "[ " + ",\n          ".join(formatted_rows) + " ]"
    
    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generate a YAML-formatted string from a dictionary.
        
        :param data: Dictionary to be converted to YAML
        :return: YAML-formatted string
        """
        lines = []
        
        # Handle top-level keys
        for key, value in data.items():
            if key == 'parts':
                lines.append(f"{key}:")
                for part in value:
                    lines.append(self._format_part(part, 1))
            else:
                lines.append(f"{key}: {self._format_value(value)}")
        
        return "\n".join(lines)
    
    def _format_part(self, part: Dict[str, Any], indent_level: int) -> str:
        """
        Format a part entry with proper indentation and nested structures.
        
        :param part: Part dictionary
        :param indent_level: Indentation level
        :return: Formatted part string
        """
        indent = " " * (self.indent_spaces * indent_level)
        lines = [f"{indent}- name: {part['name']}"]

        # Ensure layer is always present
        lines.append(f"{indent}  layer: {part.get('layer', 0)}")
        
        # Add other top-level part attributes
        for key in ['mesh', 'bones']:
            if key in part:
                if key == 'mesh':
                    lines.append(f"{indent}  {key}:")
                    lines.append(f"{indent}    grid: {self._format_list(part[key]['grid'])}")
                    lines.append(f"{indent}    points:\n{indent}      {self._format_list(part[key]['points'])}")
                elif key == 'bones':
                    lines.append(f"{indent}  {key}:")
                    for bone in part[key]:
                        lines.append(f"{indent}    - name: {bone['name']}")
                        
                        # Optional bone attributes
                        for attr in ['position', 'children', 'parent']:
                            if attr in bone:
                                # Careful handling of different attribute types
                                if attr == 'position':
                                    lines.append(f"{indent}      {attr}: {self._format_list(bone[attr])}")
                                elif attr == 'children':
                                    lines.append(f"{indent}      {attr}: {self._format_list(bone[attr])}")
                                else:  # parent
                                    lines.append(f"{indent}      {attr}: {bone[attr]}")
        
        return "\n".join(lines)

class AtlasBuilder:
    def __init__(self, ora_path):
        """Initialize the atlas builder with an ORA file path."""
        self.ora_path = ora_path
        self.model_dir = os.path.dirname(ora_path)
        
        # Create model structure matching model.json format
        self.model_data = {
            'name': os.path.basename(ora_path).split('.')[0].title(),
            'version': '1.0',
            'parts': []
        }
        
        # Extract part information from ORA file
        self.parts = self.extract_layers_from_ora(ora_path)
            
    def extract_layers_from_ora(self, ora_path):
        """Extract layers from ORA file."""
        parts = []
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(ora_path, 'r') as zf:
                zf.extractall(tmp_dir)
                
                tree = ET.parse(os.path.join(tmp_dir, 'stack.xml'))
                root = tree.getroot()
                
                layers = list(root.findall('.//layer'))
                for i, layer in enumerate(layers):
                    name = layer.get('name')
                    src = layer.get('src')
                    
                    img_path = os.path.join(tmp_dir, src)
                    if os.path.exists(img_path):
                        img = Image.open(img_path).convert('RGBA')
                        parts.insert(0, {
                            'name': name,
                            'image': img,
                            'width': img.width,
                            'height': img.height,
                            'layer': i
                        })
                        
        return parts
            
    def build_atlas(self):
        """Build texture atlas from ORA file layers."""
        # Calculate atlas size
        max_width = max(part['width'] for part in self.parts)
        total_height = sum(part['height'] for part in self.parts)

        # Create atlas image
        atlas = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
        
        # Pack images and store UV coordinates
        current_y = 0

        for part in reversed(self.parts):
            atlas.paste(part['image'], (0, current_y))
            
            grid = [2, 2]
            w, h = part['width'], part['height']
            
            points = []
            for y in range(grid[1] + 1):
                for x in range(grid[0] + 1):
                    px = round((x / grid[0] - 0.5) * (w / max(w, h)), 2)
                    py = round((y / grid[1] - 0.5) * (h / max(w, h)), 2)
                    points.extend([px, py])
            
            part_data = {
                'name': part['name'],
                'layer': part['layer'],
                'mesh': {
                    'grid': grid,
                    'points': points
                }
            }

            if 'bones' in part:
                part_data['bones'] = part['bones']
            
            if 'head' in part['name'].lower():
                part_data['bones'] = [{
                    'name': 'head_bone',
                    'position': [0, 0],
                    'children': ['eye_left_bone', 'eye_right_bone']
                }]
            elif 'eye_left' in part['name'].lower():
                part_data['bones'] = [{
                    'name': 'eye_left_bone',
                    'position': [-0.15, 0],
                    'parent': 'head_bone'
                }]
            elif 'eye_right' in part['name'].lower():
                part_data['bones'] = [{
                    'name': 'eye_right_bone',
                    'position': [0.15, 0],
                    'parent': 'head_bone'
                }]

            self.model_data['parts'].append(part_data)
            current_y += part['height']

        atlas_dir = os.path.join(self.model_dir, 'atlas')
        os.makedirs(atlas_dir, exist_ok=True)
        
        atlas_path = os.path.join(atlas_dir, 'character_atlas.png')
        atlas.save(atlas_path)
            
        # Save the complete model using YAMLGenerator
        model_path = os.path.join(atlas_dir, 'model.yaml')
        yaml_generator = YAMLGenerator()
        yaml_output = yaml_generator.generate(self.model_data)
        
        with open(model_path, 'w') as f:
            f.write(yaml_output)
            
        print(f"Atlas built successfully:")
        print(f"- Atlas image: {atlas_path}")
        print(f"- Model: {model_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python atlas_builder.py path/to/character.ora")
        sys.exit(1)
        
    builder = AtlasBuilder(sys.argv[1])
    builder.build_atlas()
