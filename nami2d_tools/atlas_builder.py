import os
import yaml
import zipfile
import tempfile
from PIL import Image
import xml.etree.ElementTree as ET

class AtlasBuilder:
    def __init__(self, ora_path):
        """Initialize the atlas builder with an ORA file path."""
        self.ora_path = ora_path
        self.model_dir = os.path.dirname(ora_path)
        
        # Create model structure matching model.json format
        self.model_data = {
            'name': os.path.basename(ora_path).split('.')[0],
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
                
                # Process layers from bottom to top for correct layer ordering
                layers = list(root.findall('.//layer'))
                for i, layer in enumerate(layers):  # Remove 'reversed' here
                    name = layer.get('name')
                    src = layer.get('src')
                    
                    img_path = os.path.join(tmp_dir, src)
                    if os.path.exists(img_path):
                        img = Image.open(img_path).convert('RGBA')
                        # Insert at beginning of list instead of appending
                        parts.insert(0, {
                            'name': name,
                            'image': img,
                            'width': img.width,
                            'height': img.height,
                            'layer': i  # Bottom-most layer starts at 0
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
        
        # Process parts in reverse order to maintain correct vertical ordering
        for part in reversed(self.parts):
            # Paste image into atlas
            atlas.paste(part['image'], (0, current_y))
            
            # Calculate UV coordinates
            uv_coords = {
                'u1': 0,
                'v1': current_y / total_height,
                'u2': part['width'] / max_width,
                'v2': (current_y + part['height']) / total_height
            }
            
            # Create grid-based mesh data
            # Using 2x2 grid as default, can be adjusted based on needs
            grid = [2, 2]
            w, h = part['width'], part['height']
            
            # Generate normalized grid points
            points = []
            for y in range(grid[1] + 1):
                for x in range(grid[0] + 1):
                    px = (x / grid[0] - 0.5) * (w / max(w, h))
                    py = (y / grid[1] - 0.5) * (h / max(w, h))
                    points.append([px, py])
            
            # Create part data matching model.json structure
            part_data = {
                'name': part['name'],
                'layer': part['layer'],
                'mesh': {
                    'grid': grid,
                    'points': points
                },
                'uv_coords': uv_coords
            }
            
            self.model_data['parts'].append(part_data)
            current_y += part['height']

        # Save atlas
        atlas_dir = os.path.join(self.model_dir, 'atlas')
        os.makedirs(atlas_dir, exist_ok=True)
        
        atlas_path = os.path.join(atlas_dir, 'character_atlas.png')
        atlas.save(atlas_path)
            
        # Save the complete model
        model_path = os.path.join(atlas_dir, 'model.yaml')
        with open(model_path, 'w') as f:
            yaml.dump(self.model_data, f)
            
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
