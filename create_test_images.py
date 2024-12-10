from PIL import Image, ImageDraw
import os

def create_test_images(output_dir):
    """Create simple test images for the character parts."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create body (blue rectangle)
    body = Image.new('RGBA', (200, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(body)
    draw.rectangle([10, 10, 190, 290], fill=(100, 100, 255, 200))
    body.save(os.path.join(output_dir, 'body.png'))
    
    # Create head (green circle)
    head = Image.new('RGBA', (150, 150), (0, 0, 0, 0))
    draw = ImageDraw.Draw(head)
    draw.ellipse([10, 10, 140, 140], fill=(100, 255, 100, 200))
    head.save(os.path.join(output_dir, 'head.png'))
    
    # Create eyes (red circles)
    eye = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(eye)
    draw.ellipse([5, 5, 35, 35], fill=(255, 100, 100, 200))
    
    eye.save(os.path.join(output_dir, 'eye_left.png'))
    eye.save(os.path.join(output_dir, 'eye_right.png'))
    
if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                             "nami2d_models", "simple_character", "parts")
    create_test_images(output_dir)
    print(f"Test images created in {output_dir}")
