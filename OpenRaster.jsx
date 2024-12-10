/*
* OpenRaster.jsx
* Opens OpenRaster (.ora) files in Photoshop CS6
* This script enables opening .ora files while preserving layers, opacity, and visibility
*/

#target photoshop

// Ensure forward slash for paths
function forwardSlash(path) {
    return path.replace(/\\/g, '/');
}

// Extract zip file using Windows built-in commands
function extractZip(zipFile, destFolder) {
    // Create the destination folder if it doesn't exist
    new Folder(destFolder).create();
    
    // Use PowerShell to extract the zip
    var psCommand = 'powershell.exe -command "& {Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory(\'' + 
                   zipFile.fsName + '\', \'' + destFolder + '\')}"';
    
    app.system(psCommand);
    $.sleep(1000); // Give time for extraction to complete
}

// Read XML file content
function readXMLFile(file) {
    if (!file.exists) return null;
    file.encoding = "UTF8";
    file.open("r");
    var content = file.read();
    file.close();
    return content;
}

// Parse dimensions from stack.xml
function getDocumentDimensions(xmlContent) {
    var imageMatch = xmlContent.match(/<image[^>]*>/);
    if (!imageMatch) throw new Error("Invalid stack.xml: no image tag found");
    
    // Try both w/h and width/height attributes
    var width = imageMatch[0].match(/(?:width|w)="(\d+)"/);
    var height = imageMatch[0].match(/(?:height|h)="(\d+)"/);
    
    if (!width || !height) throw new Error("Invalid stack.xml: missing dimensions");
    
    return {
        width: parseInt(width[1]),
        height: parseInt(height[1])
    };
}

// Convert SVG blend mode to Photoshop blend mode
function getPhotoshopBlendMode(svgMode) {
    var blendModes = {
        'svg:src-over': 'NORMAL',
        'svg:multiply': 'MULTIPLY',
        'svg:screen': 'SCREEN',
        'svg:overlay': 'OVERLAY',
        'svg:darken': 'DARKEN',
        'svg:lighten': 'LIGHTEN',
        'svg:color-dodge': 'COLORDODGE',
        'svg:color-burn': 'COLORBURN',
        'svg:hard-light': 'HARDLIGHT',
        'svg:soft-light': 'SOFTLIGHT',
        'svg:difference': 'DIFFERENCE',
        'svg:exclusion': 'EXCLUSION',
        'svg:hue': 'HUE',
        'svg:saturation': 'SATURATION',
        'svg:color': 'COLOR',
        'svg:luminosity': 'LUMINOSITY'
    };
    return blendModes[svgMode] || 'NORMAL';
}

// Move layer to exact position using bounds
function moveLayerTo(doc, layer, x, y) {
    try {
        // Ensure we're working with numbers
        x = parseInt(x) || 0;
        y = parseInt(y) || 0;
        
        // Get the layer's current position from bounds
        var bounds = layer.bounds;
        var currentX = bounds[0].value;
        var currentY = bounds[1].value;
        
        // Calculate how far we need to move to reach target position
        var deltaX = x - currentX;
        var deltaY = y - currentY;
        
        // Forcefully move the layer, even if current Y is 0
        if (deltaY !== 0) {
            layer.translate(0, deltaY);
        }
        
        // Move X separately
        if (deltaX !== 0) {
            layer.translate(deltaX, 0);
        }
        
        return true;
    } catch (e) {
        alert("Error moving layer: " + e + "\nX: " + x + ", Y: " + y + ", Current Y: " + currentY);
        return false;
    }
}

// Debugging function to log layer positions with more detail
function debugLayerPositions(doc) {
    try {
        for (var i = 0; i < doc.artLayers.length; i++) {
            var layer = doc.artLayers[i];
            var bounds = layer.bounds;
            $.writeln("Layer " + layer.name + 
                      " - X: " + bounds[0].value + 
                      ", Y: " + bounds[1].value + 
                      ", Width: " + (bounds[2].value - bounds[0].value) +
                      ", Height: " + (bounds[3].value - bounds[1].value));
        }
    } catch (e) {
        alert("Error in debugLayerPositions: " + e);
    }
}

// Create a new layer from an image file
function createLayerFromFile(doc, imageFile, layerName, opacity, visible, x, y, blendMode) {
    if (!imageFile.exists) {
        $.writeln("Error: Image file does not exist - " + imageFile.fsName);
        return null;
    }
    
    var tempDoc = null;
    try {
        // Open the image file in a temporary document
        tempDoc = app.open(imageFile);
        
        // Ensure the document is opened
        if (!tempDoc) {
            throw new Error("Could not open temporary document for " + imageFile.name);
        }
        
        // Select all and copy
        tempDoc.selection.selectAll();
        tempDoc.selection.copy();
        
        // Switch back to our target document
        app.activeDocument = doc;
        
        // Paste
        doc.paste();
        var layer = doc.activeLayer;
        
        // Set basic properties
        layer.name = layerName || "Layer";
        
        // Set layer properties
        if (opacity !== undefined) {
            try {
                layer.opacity = Math.min(100, Math.max(0, parseFloat(opacity) * 100));
            } catch (opacityError) {
                $.writeln("Warning: Could not set opacity for " + layerName + ": " + opacityError);
            }
        }
        
        if (visible !== undefined) {
            try {
                layer.visible = visible;
            } catch (visibilityError) {
                $.writeln("Warning: Could not set visibility for " + layerName + ": " + visibilityError);
            }
        }
        
        if (blendMode) {
            try {
                var psBlendMode = getPhotoshopBlendMode(blendMode);
                layer.blendMode = eval('BlendMode.' + psBlendMode);
            } catch (blendModeError) {
                $.writeln("Warning: Could not set blend mode for " + layerName + ": " + blendModeError);
            }
        }
        
        // Move the layer after it's fully created and properties are set
        if (x !== undefined && y !== undefined) {
            try {
                // Force a small delay to ensure layer is ready and bounds are accurate
                $.sleep(200);
                moveLayerTo(doc, layer, x, y);
            } catch (moveError) {
                $.writeln("Warning: Could not move layer " + layerName + ": " + moveError);
            }
        }
        
        return layer;
    } catch (e) {
        $.writeln("Error creating layer " + layerName + ": " + e);
        return null;
    } finally {
        // Ensure temporary document is closed
        if (tempDoc && tempDoc.name) {
            try {
                tempDoc.close(SaveOptions.DONOTSAVECHANGES);
            } catch (closeError) {
                $.writeln("Warning: Could not close temporary document: " + closeError);
            }
        }
    }
}

// Process layers from stack.xml
function processLayers(xmlContent, tempFolder, doc) {
    // Get all layer elements with more robust regex
    var layerRegex = /<layer[^>]*>/g;
    var layers = [];
    var match;
    
    while ((match = layerRegex.exec(xmlContent)) !== null) {
        var layerXML = match[0];
        
        // More robust parsing of layer attributes
        var parseAttribute = function(attrName) {
            // Use a more precise regex that ensures the attribute is complete
            var regex = new RegExp('\\b' + attrName + '="([^"]*)"');
            var result = layerXML.match(regex);
            return result ? result[1] : null;
        };
        
        var layer = {
            name: parseAttribute('name') || "Layer",
            src: parseAttribute('src') || "",
            opacity: parseFloat(parseAttribute('opacity') || "1.0"),
            visibility: parseAttribute('visibility') !== "hidden",
            x: parseInt(parseAttribute('x') || "0"),
            y: parseInt(parseAttribute('y') || "0"),
            blendMode: parseAttribute('composite-op')
        };
        
        // Validate layer data
        if (!layer.src) {
            $.writeln("Skipping layer without source: " + layer.name);
            continue;
        }
        
        // Add to layers list
        layers.push(layer);
    }
    
    // Process layers in reverse order (bottom to top)
    for (var i = layers.length - 1; i >= 0; i--) {
        var layer = layers[i];
        var imageFile = new File(tempFolder + "/" + layer.src);
        
        // Attempt to create layer, skip if fails
        var createdLayer = createLayerFromFile(
            doc, 
            imageFile, 
            layer.name, 
            layer.opacity, 
            layer.visibility,
            layer.x,
            layer.y,
            layer.blendMode
        );
        
        if (!createdLayer) {
            $.writeln("Failed to create layer: " + layer.name);
        }
    }
}

// Remove background layer if automatically created
function removeBackgroundLayer(doc) {
    try {
        // Check if the document has layers
        if (doc.layers.length > 0) {
            var backgroundLayer = doc.layers[doc.layers.length - 1];
            
            // Verify it's the background layer
            if (backgroundLayer.isBackgroundLayer) {
                $.writeln("Removing automatically created background layer");
                
                // Unlock the background layer
                backgroundLayer.isBackgroundLayer = false;
                
                // Delete the layer
                backgroundLayer.remove();
            }
        }
    } catch (e) {
        $.writeln("Error removing background layer: " + e);
    }
}

function main() {
    try {
        // Prompt user to select .ora file
        var oraFile = File.openDialog("Select OpenRaster (.ora) file", "OpenRaster:*.ora");
        if (!oraFile) return;
        
        // Create temporary folder for extraction
        var tempFolder = Folder.temp.fsName + "/OpenRasterTemp_" + Math.random().toString(36).substr(2, 9);
        var tempFolderObj = new Folder(tempFolder);
        tempFolderObj.create();
        
        try {
            // Extract the .ora file (which is a zip)
            extractZip(oraFile, tempFolder);
            
            // Read stack.xml
            var stackXMLFile = new File(tempFolder + "/stack.xml");
            var xmlContent = readXMLFile(stackXMLFile);
            
            // Get document dimensions
            var docDimensions = getDocumentDimensions(xmlContent);
            
            // Create a new document
            var doc = app.documents.add(
                UnitValue(docDimensions.width, "px"), 
                UnitValue(docDimensions.height, "px"), 
                72, // resolution
                "OpenRaster Document", 
                NewDocumentMode.RGB
            );
            
            // Process layers
            processLayers(xmlContent, tempFolder, doc);
            
            // Remove background layer if automatically created
            removeBackgroundLayer(doc);
            
            // Debug: log layer positions after processing
            debugLayerPositions(doc);
        } catch (e) {
            alert("Error processing OpenRaster file: " + e);
        } finally {
            // Clean up temporary folder
            tempFolderObj.remove();
        }
    } catch (e) {
        alert("Unexpected error in main function: " + e);
    }
}

main();
