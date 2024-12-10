from PIL import Image, ImageDraw
import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET

def create_test_ora(output_path):
    """Create a test ORA file with character parts as layers."""
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create temporary directory for ORA contents
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create mimetype file
        with open(os.path.join(tmp_dir, 'mimetype'), 'w') as f:
            f.write('image/openraster')
            
        # Create data directory
        data_dir = os.path.join(tmp_dir, 'data')
        os.makedirs(data_dir)
        
        # Create layers
        layers = []
        
        # Body (blue rectangle)
        body = Image.new('RGBA', (200, 300), (0, 0, 0, 0))
        draw = ImageDraw.Draw(body)
        draw.rectangle([10, 10, 190, 290], fill=(100, 100, 255, 200))
        body.save(os.path.join(data_dir, 'body.png'))
        layers.append(('body', 'body.png', 0))
        
        # Head (green circle)
        head = Image.new('RGBA', (150, 150), (0, 0, 0, 0))
        draw = ImageDraw.Draw(head)
        draw.ellipse([10, 10, 140, 140], fill=(100, 255, 100, 200))
        head.save(os.path.join(data_dir, 'head.png'))
        layers.append(('head', 'head.png', 1))
        
        # Eyes (red circles)
        eye = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(eye)
        draw.ellipse([5, 5, 35, 35], fill=(255, 100, 100, 200))
        eye.save(os.path.join(data_dir, 'eye_left.png'))
        eye.save(os.path.join(data_dir, 'eye_right.png'))
        layers.append(('eye_left', 'eye_left.png', 2))
        layers.append(('eye_right', 'eye_right.png', 2))
        
        # Create stack.xml
        root = ET.Element('image')
        root.set('version', '0.0.1')
        root.set('w', '300')
        root.set('h', '300')
        
        stack = ET.SubElement(root, 'stack')
        
        # Add layers to stack.xml in reverse order (top to bottom)
        for name, filename, layer in reversed(layers):
            layer_elem = ET.SubElement(stack, 'layer')
            layer_elem.set('name', name)
            layer_elem.set('src', f'data/{filename}')
            layer_elem.set('x', '0')
            layer_elem.set('y', '0')
            layer_elem.set('opacity', '1.0')
            
        # Save stack.xml
        tree = ET.ElementTree(root)
        tree.write(os.path.join(tmp_dir, 'stack.xml'), encoding='UTF-8', xml_declaration=True)
        
        # Create ORA file (ZIP archive)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add mimetype first (uncompressed)
            zf.write(os.path.join(tmp_dir, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # Add stack.xml
            zf.write(os.path.join(tmp_dir, 'stack.xml'), 'stack.xml')
            
            # Add layer images
            for _, filename, _ in layers:
                zf.write(os.path.join(data_dir, filename), f'data/{filename}')
    
if __name__ == "__main__":
    # Change the output path to be a file path instead of a directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                             "nami2d_models", "simple_character")
    
    # Create the ORA file path
    output_path = os.path.join(output_dir, "character.ora")
    
    create_test_ora(output_path)
    print(f"Test ORA file created at {output_path}")
