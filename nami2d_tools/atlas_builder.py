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
        
        # Create a default model structure
        self.model_data = {
            'parts': []
        }
        
        # Extract part information from ORA file
        parts = self.extract_layers_from_ora(ora_path)
        
        # Create model data from parts
        for part in parts:
            self.model_data['parts'].append({
                'name': part['name'],
                'mesh': {
                    'vertices': [[0, 0], [part['width'], 0], 
                               [part['width'], part['height']], [0, part['height']]],
                    'triangles': [[0, 1, 2], [0, 2, 3]]
                }
            })
            
    def extract_layers_from_ora(self, ora_path):
        """Extract layers from ORA file."""
        parts = []
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Extract ORA file
            with zipfile.ZipFile(ora_path, 'r') as zf:
                zf.extractall(tmp_dir)
                
                # Parse stack.xml to get layer information
                tree = ET.parse(os.path.join(tmp_dir, 'stack.xml'))
                root = tree.getroot()
                
                # Process layers
                for layer in root.findall('.//layer'):
                    name = layer.get('name')
                    src = layer.get('src')
                    
                    # Load layer image
                    img_path = os.path.join(tmp_dir, src)
                    if os.path.exists(img_path):
                        img = Image.open(img_path).convert('RGBA')
                        parts.append({
                            'name': name,
                            'image': img,
                            'width': img.width,
                            'height': img.height
                        })
                        
        return parts
            
    def build_atlas(self):
        """Build texture atlas from ORA file layers."""
        # Extract parts from ORA
        parts = self.extract_layers_from_ora(self.ora_path)
        
        # Calculate atlas size
        max_width = max(part['width'] for part in parts)
        total_height = sum(part['height'] for part in parts)

        # Create atlas image
        atlas = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
        
        # Pack images and store UV coordinates
        current_y = 0
        uv_coords = {}
        
        for part in parts:
            # Paste image into atlas
            atlas.paste(part['image'], (0, current_y))
            
            # Calculate UV coordinates
            uv_coords[part['name']] = {
                'u1': 0,
                'v1': current_y / total_height,
                'u2': part['width'] / max_width,
                'v2': (current_y + part['height']) / total_height
            }
            
            current_y += part['height']

        # Save atlas
        atlas_dir = os.path.join(self.model_dir, 'atlas')
        os.makedirs(atlas_dir, exist_ok=True)
        
        atlas_path = os.path.join(atlas_dir, 'character_atlas.png')
        atlas.save(atlas_path)
        
        # Save UV coordinates
        # uv_path = os.path.join(atlas_dir, 'atlas_map.yaml')
        # with open(uv_path, 'w') as f:
        #     yaml.dump(uv_coords, f)
            
        # Update model with UV coordinates
        for part in self.model_data['parts']:
            part['uv_coords'] = uv_coords[part['name']]
            
        # Save the complete model
        model_path = os.path.join(atlas_dir, 'model.yaml')
        with open(model_path, 'w') as f:
            yaml.dump(self.model_data, f)
            
        print(f"Atlas built successfully:")
        print(f"- Atlas image: {atlas_path}")
        #print(f"- UV mapping: {uv_path}")
        print(f"- Model: {model_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python atlas_builder.py path/to/character.ora")
        sys.exit(1)
        
    builder = AtlasBuilder(sys.argv[1])
    builder.build_atlas()