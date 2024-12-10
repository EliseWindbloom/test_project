import os
import json
from PIL import Image
import numpy as np

class AtlasBuilder:
    def __init__(self, model_path):
        """Initialize the atlas builder with a model path."""
        self.model_path = model_path
        self.model_dir = os.path.dirname(model_path)
        
        # Load model definition
        with open(model_path, 'r') as f:
            self.model_data = json.load(f)
            
    def build_atlas(self):
        """Build texture atlas from individual part images."""
        parts = []
        max_width = 0
        total_height = 0
        
        # First pass: load all images and calculate atlas size
        for part in self.model_data['parts']:
            img_path = os.path.join(self.model_dir, part['file'])
            img = Image.open(img_path).convert('RGBA')
            parts.append({
                'name': part['name'],
                'image': img,
                'width': img.width,
                'height': img.height
            })
            max_width = max(max_width, img.width)
            total_height += img.height

        # Create atlas image
        atlas = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
        
        # Second pass: pack images and store UV coordinates
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
        uv_path = os.path.join(atlas_dir, 'atlas_map.json')
        with open(uv_path, 'w') as f:
            json.dump(uv_coords, f, indent=4)
            
        # Update model with UV coordinates
        for part in self.model_data['parts']:
            part['uv_coords'] = uv_coords[part['name']]
            
        model_path = os.path.join(atlas_dir, 'model_runtime.json')
        with open(model_path, 'w') as f:
            json.dump(self.model_data, f, indent=4)
            
        print(f"Atlas built successfully:")
        print(f"- Atlas image: {atlas_path}")
        print(f"- UV mapping: {uv_path}")
        print(f"- Runtime model: {model_path}")
        
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python atlas_builder.py path/to/model.json")
        sys.exit(1)
        
    builder = AtlasBuilder(sys.argv[1])
    builder.build_atlas()
