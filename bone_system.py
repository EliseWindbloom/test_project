import pygame
import math

class Bone:
    def __init__(self, x, y, length, angle=0):
        self.x, self.y, self.original_length, self.angle = x, y, length, angle
        self.length = length  # This will be updated based on sprite size
        self.parent = None
        self.selected = False
        self.sprite = None
        self.sprite_original = None
        
        # Visual positioning - the fixed visual position of the sprite
        self.visual_x = x
        self.visual_y = y
        
        # Anchor point (0-1 normalized coordinates within the sprite)
        self.anchor_x = 0.5
        self.anchor_y = 0.5
    
    def load_sprite(self, sprite_path, auto_anchor=True):
        """Load sprite and set up anchoring"""
        try:
            self.sprite_original = pygame.image.load(sprite_path).convert_alpha()
            self.sprite = self.sprite_original
            # Adjust bone length to match sprite width
            self.length = self.sprite_original.get_width()
            
            if auto_anchor:
                self.set_anchor_from_filename(sprite_path)
                
            print(f"Bone length adjusted to sprite width: {self.length}")
        except pygame.error:
            print(f"Could not load sprite: {sprite_path}, using original length: {self.original_length}")
            self.sprite = None
            self.sprite_original = None
            self.length = self.original_length
    
    def set_anchor_from_filename(self, filename):
        """Set anchor point based on filename conventions"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(('_l.png', '_left.png')):
            # Left side (anchor to right side from character's perspective)
            self.anchor_x, self.anchor_y = 1.0, 0.5
        elif filename_lower.endswith(('_r.png', '_right.png')):
            # Right side (anchor to left side from character's perspective)
            self.anchor_x, self.anchor_y = 0.0, 0.5
        elif filename_lower.endswith(('_u.png', '_up.png')):
            # Up side (anchor to bottom)
            self.anchor_x, self.anchor_y = 0.5, 1.0
        elif filename_lower.endswith(('_d.png', '_down.png')):
            # Down side (anchor to top)
            self.anchor_x, self.anchor_y = 0.5, 0.0
        else:
            # Auto-determine based on dimensions
            if self.sprite_original:
                width = self.sprite_original.get_width()
                height = self.sprite_original.get_height()
                if width >= height:
                    # Width >= height: left-center anchor (bone starts from left side)
                    self.anchor_x, self.anchor_y = 0.0, 0.5
                else:
                    # Height > width: center-top anchor (bone starts from top)
                    self.anchor_x, self.anchor_y = 0.5, 0.0
            else:
                # Default to left-center if no sprite (matches original bone behavior)
                self.anchor_x, self.anchor_y = 0.0, 0.5
    
    def set_anchor(self, anchor_x, anchor_y):
        """Manually set anchor point"""
        self.anchor_x = max(0.0, min(1.0, anchor_x))
        self.anchor_y = max(0.0, min(1.0, anchor_y))
    
    def get_anchor_world_pos(self):
        """Get the world position of the anchor point"""
        if not self.sprite_original:
            return self.visual_x, self.visual_y
            
        anchor_x = self.visual_x + self.anchor_x * self.sprite_original.get_width()
        anchor_y = self.visual_y + self.anchor_y * self.sprite_original.get_height()
        return anchor_x, anchor_y
    
    def follow(self, tx, ty):
        """Make the bone follow the target position - FIXED for IK"""
        # This is the key fix: use the original logic from the working version
        target = pygame.math.Vector2(tx - self.x, ty - self.y)
        self.angle = math.atan2(target.y, target.x)
        if target.length() > 0:
            target.normalize_ip()
            target *= self.length
            self.x, self.y = tx - target.x, ty - target.y
        
        # Update visual position based on new bone position
        self.update_visual_position()
    
    def update_visual_position(self):
        """Update visual position based on bone position and anchor"""
        if self.sprite_original:
            offset_x = self.anchor_x * self.sprite_original.get_width()
            offset_y = self.anchor_y * self.sprite_original.get_height()
            self.visual_x = self.x - offset_x
            self.visual_y = self.y - offset_y
        else:
            self.visual_x = self.x
            self.visual_y = self.y
    
    def end_pos(self):
        """Get the end position of the bone (from anchor point)"""
        return self.x + math.cos(self.angle) * self.length, self.y + math.sin(self.angle) * self.length
    
    def update(self):
        """Update bone position based on parent"""
        if self.parent:
            parent_end_x, parent_end_y = self.parent.end_pos()
            self.x, self.y = parent_end_x, parent_end_y
            self.update_visual_position()
    
    def contains(self, px, py):
        ex, ey = self.end_pos()
        # Point to line distance
        A, B, C, D = px - self.x, py - self.y, ex - self.x, ey - self.y
        t = max(0, min(1, (A*C + B*D) / (C*C + D*D) if C*C + D*D else 0))
        dx, dy = px - (self.x + t*C), py - (self.y + t*D)
        return dx*dx + dy*dy < 225  # 15^2
    
    def draw(self, screen, visibility_mode):
        """Draw based on visibility mode"""
        ex, ey = self.end_pos()
        
        # Visibility modes: 0=All, 1=Sprites only, 2=Sprites+Joints, 3=Joints only, 4=Joints+Lines, 5=Lines only
        show_sprite = visibility_mode in [0, 1, 2]
        show_joints = visibility_mode in [0, 2, 3, 4]
        show_lines = visibility_mode in [0, 4, 5]
        
        # Draw sprite if available and visible
        if show_sprite and self.sprite and self.sprite_original:
            # Rotate sprite to match bone angle
            angle_degrees = math.degrees(self.angle)
            rotated_sprite = pygame.transform.rotate(self.sprite_original, -angle_degrees)
            
            # Calculate where to draw the rotated sprite so the anchor point stays at bone position
            width, height = self.sprite_original.get_width(), self.sprite_original.get_height()
            
            # Calculate anchor point in original image space
            anchor_px = self.anchor_x * width
            anchor_py = self.anchor_y * height
            
            # Calculate center offset from anchor in original image
            center_x, center_y = width / 2, height / 2
            offset_x = center_x - anchor_px
            offset_y = center_y - anchor_py
            
            # Rotate the offset vector
            angle_rad = math.radians(angle_degrees)  # Note: positive angle for correct rotation
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            
            rotated_offset_x = offset_x * cos_a - offset_y * sin_a
            rotated_offset_y = offset_x * sin_a + offset_y * cos_a
            
            # Position the rotated sprite so the anchor appears at bone position
            draw_x = self.x + rotated_offset_x - rotated_sprite.get_width() / 2
            draw_y = self.y + rotated_offset_y - rotated_sprite.get_height() / 2
            
            # Draw the sprite
            screen.blit(rotated_sprite, (draw_x, draw_y))
        
        # Draw line if visible
        if show_lines:
            color = (255, 255, 0) if self.selected else (255, 255, 255)
            line_width = 8 if not show_sprite else 4
            pygame.draw.line(screen, color, (self.x, self.y), (ex, ey), line_width)
        
        # Draw joints if visible
        if show_joints:
            joint_size = 12 if not show_sprite else 8
            end_size = 8 if not show_sprite else 6
            pygame.draw.circle(screen, (255, 255, 0) if self.selected else (255, 0, 0), (int(self.x), int(self.y)), joint_size)
            pygame.draw.circle(screen, (0, 255, 0), (int(ex), int(ey)), end_size)

class Chain:
    def __init__(self, x, y, lengths, is_ik=False, positions=None, anchors=None, sprite_paths=None, parent_skeleton=None):
        """
        Initialize a bone chain with optional custom positions and anchors
        
        Args:
            x, y: Starting position (used if positions is None)
            lengths: List of bone lengths
            is_ik: Whether this is an IK chain
            positions: Optional list of (x, y) tuples for each bone's visual position
            anchors: Optional list of (anchor_x, anchor_y) tuples for each bone
            sprite_paths: Optional list of sprite paths for each bone
            parent_skeleton: Reference to parent skeleton (if any)
        """
        self.bones = []
        self.parent_skeleton = parent_skeleton
        self.local_x, self.local_y = x, y  # Local position relative to skeleton
        
        # Create bones with custom positions if provided
        for i in range(len(lengths)):
            if positions and i < len(positions):
                bone_x, bone_y = positions[i]
            elif i == 0:
                bone_x, bone_y = self.get_world_x(), self.get_world_y()
            else:
                # Will be updated when parent is set
                bone_x, bone_y = self.get_world_x(), self.get_world_y()
            
            bone = Bone(bone_x, bone_y, lengths[i])
            
            # Set parent relationship
            if i > 0:
                bone.parent = self.bones[i-1]
            
            self.bones.append(bone)
        
        # Load sprites and set anchors
        for i, bone in enumerate(self.bones):
            # Load sprite
            if sprite_paths and i < len(sprite_paths):
                bone.load_sprite(sprite_paths[i], auto_anchor=(anchors is None))
            else:
                bone.load_sprite("bone.png", auto_anchor=(anchors is None))
            
            # Set custom anchor if provided
            if anchors and i < len(anchors):
                bone.set_anchor(anchors[i][0], anchors[i][1])
        
        # Update positions for bones without custom positions
        if not positions:
            for bone in self.bones:
                bone.update()
        else:
            # If custom positions were provided, update visual positions
            for bone in self.bones:
                bone.update_visual_position()
        
        self.is_ik = is_ik
        self.mode = 0  # 0=Animated, 1=Static, 2=Mouse, 3=Keyboard
        self.selected = 0
        self.bones[0].selected = True
        
        # Calculate target position for IK
        if self.is_ik:
            total_length = sum(bone.length for bone in self.bones)
            self.target = [self.get_world_x() + total_length, self.get_world_y()]
            
    
    def get_world_x(self):
        """Get world X coordinate (local + skeleton offset)"""
        return self.local_x + (self.parent_skeleton.x if self.parent_skeleton else 0)
    
    def get_world_y(self):
        """Get world Y coordinate (local + skeleton offset)"""
        return self.local_y + (self.parent_skeleton.y if self.parent_skeleton else 0)
    
    def update_world_positions(self):
        """Update all bone positions when skeleton moves"""
        if not self.parent_skeleton:
            return
            
        # Update base bone position
        self.bones[0].x = self.get_world_x()
        self.bones[0].y = self.get_world_y()
        self.bones[0].update_visual_position()
        
        # Update rest of chain
        if self.is_ik and hasattr(self, 'target'):
            # For IK chains, re-run IK with current target
            self.ik(*self.target)
        else:
            # For FK chains, update forward kinematics
            self.fk()
    
    def fk(self):
        for bone in self.bones:
            bone.update()
    
    def ik(self, tx, ty):
        # Store the base position (this is crucial - the first bone should stay anchored)
        base = self.bones[0].x, self.bones[0].y
        
        # Forward pass - work backwards from target
        self.bones[-1].follow(tx, ty)
        for i in range(len(self.bones) - 2, -1, -1):
            self.bones[i].follow(self.bones[i+1].x, self.bones[i+1].y)
        
        # Backward pass - restore base and work forwards
        self.bones[0].x, self.bones[0].y = base
        self.bones[0].update_visual_position()  # Update visual position after restoring base
        
        for i in range(1, len(self.bones)):
            px, py = self.bones[i-1].end_pos()
            ex, ey = self.bones[i].end_pos()
            dx, dy = ex - px, ey - py
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                dx, dy = dx/dist * self.bones[i].length, dy/dist * self.bones[i].length
                self.bones[i].x, self.bones[i].y = px, py
                self.bones[i].angle = math.atan2(dy, dx)
                
                # Update visual position based on new bone position
                self.bones[i].update_visual_position()
    
    def select_bone(self, mx, my):
        if not self.is_ik:
            for i, bone in enumerate(self.bones):
                if bone.contains(mx, my):
                    for b in self.bones: b.selected = False
                    bone.selected = True
                    self.selected = i
                    return True
        return False
    
    def update(self, time, mx, my, keys):
        if self.mode == 0:  # Animated
            if self.is_ik:
                self.target[0] = self.get_world_x() + 100 + math.cos(time*2) * 80
                self.target[1] = self.get_world_y() + math.sin(time*3) * 40
                self.ik(*self.target)
            else:
                angles = [math.sin(time*2)*0.5, math.sin(time*3)*0.7, math.sin(time*4)*0.9]
                for i, angle in enumerate(angles[:len(self.bones)]):
                    self.bones[i].angle = angle
                self.fk()
        elif self.mode == 2:  # Mouse
            if self.is_ik:
                self.target = [mx, my]
                self.ik(mx, my)
            else:
                dx, dy = mx - self.bones[self.selected].x, my - self.bones[self.selected].y
                self.bones[self.selected].angle = math.atan2(dy, dx)
                self.fk()
        elif self.mode == 3:  # Keyboard
            spd = 3 if self.is_ik else 0.05
            if self.is_ik:
                if keys[pygame.K_LEFT]: self.target[0] -= spd
                if keys[pygame.K_RIGHT]: self.target[0] += spd
                if keys[pygame.K_UP]: self.target[1] -= spd
                if keys[pygame.K_DOWN]: self.target[1] += spd
                self.ik(*self.target)
            else:
                if keys[pygame.K_LEFT]: self.bones[self.selected].angle -= spd
                if keys[pygame.K_RIGHT]: self.bones[self.selected].angle += spd
                if keys[pygame.K_UP]:
                    self.bones[self.selected].selected = False
                    self.selected = (self.selected - 1) % len(self.bones)
                    self.bones[self.selected].selected = True
                if keys[pygame.K_DOWN]:
                    self.bones[self.selected].selected = False
                    self.selected = (self.selected + 1) % len(self.bones)
                    self.bones[self.selected].selected = True
                self.fk()
    
    def draw(self, screen, visibility_mode):
        for bone in self.bones:
            bone.draw(screen, visibility_mode)
        if self.is_ik and self.mode in [0, 2, 3]:
            pygame.draw.circle(screen, (255, 255, 0), (int(self.target[0]), int(self.target[1])), 15, 3)

class Skeleton:
    def __init__(self, name, x=0, y=0, chains=None):
        """
        Initialize a skeleton container for bone chains
        
        Args:
            name: Name of the skeleton
            x, y: World position of the skeleton
            chains: List of chain configurations as dicts or Chain objects
        """
        self.name = name
        self.x = x
        self.y = y
        self.chains = []
        
        # Add chains if provided
        if chains:
            for chain_config in chains:
                if isinstance(chain_config, Chain):
                    # Already a Chain object, just set parent
                    chain_config.parent_skeleton = self
                    self.chains.append(chain_config)
                elif isinstance(chain_config, dict):
                    # Dictionary configuration
                    self.add_chain(**chain_config)
            # Ensure all chains have correct world positions from the start
            for chain in self.chains:
                chain.update_world_positions()
    
    def add_chain(self, x, y, lengths, is_ik=False, positions=None, anchors=None, sprite_paths=None):
        """Add a new chain to this skeleton"""
        chain = Chain(x, y, lengths, is_ik, positions, anchors, sprite_paths, parent_skeleton=self)
        self.chains.append(chain)
        return chain
    
    def move(self, dx, dy):
        """Move the skeleton and update all chains"""
        self.x += dx
        self.y += dy
        for chain in self.chains:
            chain.update_world_positions()
    
    def set_position(self, x, y):
        """Set absolute position of the skeleton"""
        self.x = x
        self.y = y
        for chain in self.chains:
            chain.update_world_positions()
    
    def update(self, time, mx, my, keys):
        """Update all chains in this skeleton"""
        for chain in self.chains:
            chain.update(time, mx, my, keys)
    
    def draw(self, screen, visibility_mode):
        """Draw all chains in this skeleton"""
        for chain in self.chains:
            chain.draw(screen, visibility_mode)
    
    def select_bone(self, mx, my):
        """Try to select a bone in any of the chains"""
        for chain in self.chains:
            if chain.select_bone(mx, my):
                return True
        return False

def unified_demo():
    """Unified demo that can switch between standard kinematics and skeleton system"""
    pygame.init()
    W, H = 1200, 800
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("2D Bone System with Skeleton - Demo")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)
    
    # Demo mode: 0 = Standard Kinematics, 1 = Skeleton System
    demo_mode = 0
    
    # Standard kinematics chains
    fk_standard = Chain(200, H//2, [80, 70, 60])
    ik_standard = Chain(800, H//2, [80, 70, 60], True)
    
    # Custom positioned bones example using Skeleton
    custom_positions = [(0, 0), (150, -50), (300, -100)]  # Relative to skeleton position
    custom_anchors = [(0.0, 0.5), (0.5, 0.5), (1.0, 0.5)]  # left, center, right anchors
    sprite_paths = ["bone.png", "bone.png", "bone.png"]
    
    # Create skeleton with a chain - Fixed: Initialize at a proper screen position
    skeleton = Skeleton(
        name="Demo Character",
        x=300, y=300,  # Start at center-ish position
        chains=[{
            'x': 0, 'y': 0,  # Local position within skeleton
            'lengths': [100, 100, 100],
            'is_ik': True,
            'positions': custom_positions,
            'anchors': custom_anchors,
            'sprite_paths': sprite_paths
        }]
    )
    
    modes = ["Animated", "Static", "Mouse", "Keyboard"]
    visibility_modes = ["All", "Sprites Only", "Sprites + Joints", "Joints Only", "Joints + Lines", "Lines Only"]
    visibility_mode = 0
    time = 0
    
    # Movement speed for skeleton
    skeleton_move_speed = 5
    
    while True:
        dt = clock.tick(60) / 1000.0
        time += dt
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_F1:
                    demo_mode = (demo_mode + 1) % 2
                elif event.key == pygame.K_v:
                    visibility_mode = (visibility_mode + 1) % len(visibility_modes)
                elif demo_mode == 0:  # Standard kinematics mode
                    if event.key == pygame.K_q:
                        fk_standard.mode = (fk_standard.mode + 1) % 4
                    elif event.key == pygame.K_e:
                        ik_standard.mode = (ik_standard.mode + 1) % 4
                elif demo_mode == 1:  # Skeleton system mode
                    if event.key == pygame.K_q:
                        skeleton.chains[0].mode = (skeleton.chains[0].mode + 1) % 4
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if demo_mode == 0 and mx < W//2:
                    fk_standard.select_bone(mx, my)
        
        # Handle continuous key movement for skeleton (moved outside event loop)
        if demo_mode == 1:  # Skeleton system mode
            if keys[pygame.K_w]:
                skeleton.move(0, -skeleton_move_speed)
            if keys[pygame.K_s]:
                skeleton.move(0, skeleton_move_speed)
            if keys[pygame.K_a]:
                skeleton.move(-skeleton_move_speed, 0)
            if keys[pygame.K_d]:
                skeleton.move(skeleton_move_speed, 0)
        
        # Update based on demo mode
        if demo_mode == 0:  # Standard kinematics
            fk_standard.update(time, mx, my, keys)
            ik_standard.update(time, mx, my, keys)
        else:  # Skeleton system
            skeleton.update(time, mx, my, keys)
        
        # Draw
        screen.fill((20, 20, 30))
        
        if demo_mode == 0:  # Standard kinematics
            fk_standard.draw(screen, visibility_mode)
            ik_standard.draw(screen, visibility_mode)
            
            # UI for standard mode
            screen.blit(font.render(f"Forward Kinematics - {modes[fk_standard.mode]}", True, (255, 255, 255)), (50, 50))
            screen.blit(font.render(f"Inverse Kinematics - {modes[ik_standard.mode]}", True, (255, 255, 255)), (650, 50))
            screen.blit(font.render(f"FK Selected Bone: {fk_standard.selected + 1}/{len(fk_standard.bones)}", True, (200, 200, 200)), (50, 110))
            
            # Draw divider line
            pygame.draw.line(screen, (100, 100, 100), (W//2, 0), (W//2, H), 2)
            
        else:  # Skeleton system
            skeleton.draw(screen, visibility_mode)
            
            # UI for skeleton mode
            chain = skeleton.chains[0]  # Get the first chain for display info
            screen.blit(font.render(f"Skeleton: {skeleton.name} - {modes[chain.mode]}", True, (255, 255, 255)), (50, 50))
            screen.blit(font.render(f"Position: ({skeleton.x:.0f}, {skeleton.y:.0f})", True, (200, 200, 200)), (50, 110))
            screen.blit(font.render("Skeleton with custom positioned bones and anchors", True, (200, 200, 200)), (50, 140))
        
        # Common UI
        demo_names = ["Standard Kinematics", "Skeleton System"]
        screen.blit(font.render(f"Demo Mode: {demo_names[demo_mode]}", True, (255, 255, 100)), (50, 80))
        screen.blit(font.render(f"Visibility: {visibility_modes[visibility_mode]}", True, (255, 255, 100)), (400, 80))
        
        # Instructions
        if demo_mode == 0:  # Standard kinematics instructions
            instructions = [
                "F1 - Switch Demo Mode | V - Cycle Visibility | ESC - Exit",
                "Q - Cycle FK Mode | E - Cycle IK Mode",
                "FK Mouse: Click bone to select, then move mouse",
                "FK Keyboard: Arrow keys rotate, Up/Down select bone",
                "IK Mouse: Move mouse to control target",
                "IK Keyboard: Arrow keys move target"
            ]
        else:  # Skeleton system instructions
            instructions = [
                "F1 - Switch Demo Mode | V - Cycle Visibility | ESC - Exit",
                "Q - Cycle Mode (Animated/Static/Mouse/Keyboard)",
                "WASD - Move Skeleton Position (hold keys down)",
                "Mouse Mode: Move mouse to control IK target",
                "Keyboard Mode: Arrow keys move IK target",
                "Skeleton system ready for PSD layer conversion!"
            ]
        
        for i, text in enumerate(instructions):
            screen.blit(font.render(text, True, (200, 200, 200)), (50, H - 160 + i * 25))
        
        pygame.display.flip()

def main():
    unified_demo()
    pygame.quit()

if __name__ == "__main__":
    main()