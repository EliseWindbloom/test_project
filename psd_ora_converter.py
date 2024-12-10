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
            # Create data directory for layer images
            data_dir = os.path.join(tmpdirname, 'data')
            os.makedirs(data_dir)

            # Create mimetype file
            with open(os.path.join(tmpdirname, 'mimetype'), 'w') as f:
                f.write('image/openraster')
            
            # Create stack.xml
            stack_xml_path = os.path.join(tmpdirname, 'stack.xml')
            with open(stack_xml_path, 'w') as f:
                # Header with image attributes
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(f'<image xres="100" h="{psd.height}" version="0.0.1" w="{psd.width}" yres="100">\n')
                
                # Root stack element
                f.write('  <stack name="root" isolation="isolate" x="0" composite-op="svg:src-over" '
                       'visibility="visible" opacity="1" y="0">\n')
                
                # Process layers in reverse order to maintain proper stacking
                layers = list(reversed(list(psd)))
                for i, layer in enumerate(layers):
                    if layer.is_group():
                        continue  # Skip group layers for now
                        
                    layer_image = layer.topil()
                    if layer_image is None:
                        continue
                        
                    # Convert RGBA if necessary
                    if layer_image.mode != 'RGBA':
                        layer_image = layer_image.convert('RGBA')

                    # Reverse the layer index
                    i_reverse = len(layers) - 1 - i

                    # Save layer image in data directory
                    layer_filename = f'layer{i_reverse}.png'
                    layer_path = os.path.join(data_dir, layer_filename)
                    layer_image.save(layer_path)
                    
                    # Layer name (use original name or default)
                    layer_name = layer.name or f"Paint Layer {i}"
                    
                    # Determine if this is the background layer
                    is_background = i == len(layers) - 1
                    
                    # Write layer element with all required attributes
                    layer_xml = (
                        '    <layer name="' + layer_name + '" '
                        'x="' + str(layer.offset[0] if layer.offset else 0) + '" '
                        'composite-op="svg:src-over" '
                        'src="data/' + layer_filename + '" '
                        'visibility="' + ("visible" if layer.visible else "hidden") + '" '
                        'opacity="' + f"{layer.opacity / 255.0:.2f}" + '" '
                        + ('edit-locked="true" ' if is_background else "") +
                        'y="' + str(layer.offset[1] if layer.offset else 0) + '"/>'
                    )

                    f.write(layer_xml + '\n')
                
                # Close stack and image elements
                f.write('  </stack>\n')
                f.write('</image>')

            # Create merged image (composite of all layers)
            merged_image = psd.compose()
            merged_path = os.path.join(tmpdirname, 'mergedimage.png')
            merged_image.save(merged_path)

            # Create thumbnails directory and thumbnail
            thumbnails_dir = os.path.join(tmpdirname, 'Thumbnails')
            os.makedirs(thumbnails_dir)

            # Create thumbnail (256x256 max size)
            thumb_size = (256, 256)
            thumbnail = merged_image.copy()
            thumbnail.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            thumbnail_path = os.path.join(thumbnails_dir, 'thumbnail.png')
            thumbnail.save(thumbnail_path)
            
            # Create ORA file (ZIP archive)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add mimetype first, uncompressed
                zf.write(os.path.join(tmpdirname, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
                
                # Add stack.xml
                zf.write(stack_xml_path, 'stack.xml')
                
                # Add merged image
                zf.write(merged_path, 'mergedimage.png')
                
                # Add thumbnail
                zf.write(thumbnail_path, 'Thumbnails/thumbnail.png')
                
                # Add layer images from data directory
                for filename in os.listdir(data_dir):
                    zf.write(os.path.join(data_dir, filename), f'data/{filename}')
        
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
