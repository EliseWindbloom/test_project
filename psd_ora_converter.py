import argparse
import logging
import os
import tempfile
from typing import Union

try:
    from psd_tools import PSDImage
    import zipfile
    from PIL import Image
except ImportError as e:
    print(f"Error: Required libraries not found. Please install psd-tools and Pillow.")
    print(f"You can install them using: pip install psd-tools Pillow")
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def convert_psd_to_ora(psd_path: str, output_path: str = None) -> str:
    """
    Convert a PSD file to ORA format.
    
    :param psd_path: Path to the input PSD file
    :param output_path: Optional path for the output ORA file
    :return: Path to the created ORA file
    """
    try:
        # Open the PSD file
        psd = PSDImage.open(psd_path)
        
        # Determine output path if not provided
        if output_path is None:
            output_path = os.path.splitext(psd_path)[0] + '.ora'
        
        # Create a temporary directory for ORA contents
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create stack.xml
            stack_xml_path = os.path.join(tmpdirname, 'stack.xml')
            with open(stack_xml_path, 'w') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<image>\n')
                f.write(f'  <width>{psd.width}</width>\n')
                f.write(f'  <height>{psd.height}</height>\n')
                f.write('  <stack>\n')
                
                # Save layers
                for i, layer in enumerate(psd):
                    layer_image = layer.topil()
                    layer_path = os.path.join(tmpdirname, f'layer{i}.png')
                    layer_image.save(layer_path)
                    
                    f.write('    <layer>\n')
                    f.write(f'      <name>{layer.name}</name>\n')
                    f.write(f'      <src>layer{i}.png</src>\n')
                    f.write(f'      <opacity>{layer.opacity/255.0:.2f}</opacity>\n')
                    f.write(f'      <visibility>{"visible" if layer.visible else "hidden"}</visibility>\n')
                    f.write('    </layer>\n')
                
                f.write('  </stack>\n')
                f.write('</image>')
            
            # Create ORA file (ZIP archive)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(stack_xml_path, 'stack.xml')
                
                # Add layer images
                for filename in os.listdir(tmpdirname):
                    if filename.endswith('.png'):
                        zf.write(os.path.join(tmpdirname, filename), filename)
        
        logger.info(f"Successfully converted {psd_path} to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error converting PSD to ORA: {e}")
        raise

def convert_ora_to_psd(ora_path: str, output_path: str = None) -> str:
    """
    Convert an ORA file to PSD format.
    
    :param ora_path: Path to the input ORA file
    :param output_path: Optional path for the output PSD file
    :return: Path to the created PSD file
    """
    try:
        # Determine output path if not provided
        if output_path is None:
            output_path = os.path.splitext(ora_path)[0] + '.psd'
        
        # Extract ORA file
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Manually extract the ORA file
            with zipfile.ZipFile(ora_path, 'r') as zf:
                # Create a list to store extracted layer paths
                layer_paths = []
                
                # Extract stack.xml first
                zf.extract('stack.xml', path=tmpdirname)
                
                # Attempt to find layers in both 'data/' and root directories
                for filename in zf.namelist():
                    # Check for PNG files in 'data/' or root directory
                    if filename.endswith('.png') and (filename.startswith('data/') or not filename.startswith('data')):
                        # Extract the file to a known location
                        extracted_path = os.path.join(tmpdirname, os.path.basename(filename))
                        with zf.open(filename) as source, open(extracted_path, 'wb') as target:
                            target.write(source.read())
                        layer_paths.append(extracted_path)
                
                # Parse stack.xml
                import xml.etree.ElementTree as ET
                try:
                    tree = ET.parse(os.path.join(tmpdirname, 'stack.xml'))
                    root = tree.getroot()
                except ET.ParseError as xml_error:
                    logger.error(f"Error parsing stack.xml: {xml_error}")
                    raise
                
                # Get image dimensions
                width = int(root.find('width').text if root.find('width') is not None else 512)
                height = int(root.find('height').text if root.find('height') is not None else 512)
                
                # Create base PSD image
                psd = PSDImage.new(
                    mode='RGBA', 
                    size=(width, height), 
                    color=(255, 255, 255, 0)
                )
                
                # Add layers
                stack = root.find('stack')
                if stack is not None:
                    # Reverse the order to match PSD layer stacking
                    layers = list(reversed(stack.findall('layer')))
                    for layer_elem in layers:
                        # Get layer details
                        name = layer_elem.find('name').text if layer_elem.find('name') is not None else f'Layer {len(psd)}'
                        src = layer_elem.find('src').text if layer_elem.find('src') is not None else None
                        
                        if not src:
                            continue
                        
                        # Find the corresponding extracted layer image
                        layer_filename = os.path.basename(src)
                        layer_path = os.path.join(tmpdirname, layer_filename)
                        
                        # Verify the file exists
                        if not os.path.exists(layer_path):
                            logger.warning(f"Layer image not found: {layer_path}")
                            continue
                        
                        # Load layer image
                        try:
                            layer_image = Image.open(layer_path)
                        except Exception as e:
                            logger.warning(f"Could not load layer {name}: {e}")
                            continue
                        
                        # Get opacity and visibility
                        opacity_elem = layer_elem.find('opacity')
                        visibility_elem = layer_elem.find('visibility')
                        
                        opacity = float(opacity_elem.text if opacity_elem is not None else 1.0)
                        visibility = visibility_elem is None or visibility_elem.text == 'visible'
                        
                        # Add layer to PSD
                        psd_layer = psd.add_layer(layer_image, name=name)
                        psd_layer.opacity = int(opacity * 255)  # Convert to 0-255 range
                        psd_layer.visible = visibility
                
                # Save PSD file
                psd.save(output_path)
        
        logger.info(f"Successfully converted {ora_path} to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error converting ORA to PSD: {e}")
        raise

def main():
    """
    Command-line interface for file conversion.
    """
    parser = argparse.ArgumentParser(description='Convert between PSD and ORA file formats')
    parser.add_argument('input_file', help='Path to the input file (PSD or ORA)')
    parser.add_argument('-o', '--output', help='Path to the output file (optional)')
    
    args = parser.parse_args()
    
    # Determine conversion direction based on file extension
    input_ext = os.path.splitext(args.input_file)[1].lower()
    
    try:
        if input_ext == '.psd':
            convert_psd_to_ora(args.input_file, args.output)
        elif input_ext == '.ora':
            convert_ora_to_psd(args.input_file, args.output)
        else:
            logger.error(f"Unsupported file format: {input_ext}. Use .psd or .ora files.")
            return 1
    
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    main()
