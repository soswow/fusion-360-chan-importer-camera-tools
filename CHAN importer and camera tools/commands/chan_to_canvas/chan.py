from typing import List
import adsk.core
import math

class ChanFrame:
    def __init__(self, frame, loc_x, loc_y, loc_z, rot_x, rot_y, rot_z, angle_y):
        self.frame = frame
        self.location = adsk.core.Point3D.create(loc_x, loc_y, loc_z)
        self.rotation_euler = (rot_x, rot_y, rot_z)  # Pitch, Yaw, Roll (radians)
        self.angle_y = angle_y
    
    def __repr__(self):
        return (f"ChanFrame(frame={self.frame}, "
                f"location=({self.location.x:.2f}, {self.location.y:.2f}, {self.location.z:.2f}), "
                f"rotation_euler=({self.rotation_euler[0]:.2f}, {self.rotation_euler[1]:.2f}, {self.rotation_euler[2]:.2f}), "
                f"angle_y={self.angle_y:.2f})")


def parse_chan_file(filepath, scale_factor=1):
    """
    Parses a .CHAN file and returns the camera animation data as a list of ChanFrame instances.
    
    Args:
        filepath (str): The path to the .CHAN file.
        
    Returns:
        list: A list of ChanFrame instances where each instance represents a frame's data.
    """
    chan_frames: List[ChanFrame] = []
    
    try:
        with open(filepath, 'r') as file:
            for line in file:
                # Strip any extra whitespace and split by spaces
                values = line.strip().split()
                
                # Create an instance of ChanFrame
                frame_data = ChanFrame(
                    frame = int(values[0]),
                    loc_x = float(values[1]) * scale_factor,
                    loc_y = float(values[2]) * scale_factor,
                    loc_z = float(values[3]) * scale_factor,
                    rot_x = math.radians(float(values[4])),
                    rot_y = math.radians(float(values[5])),
                    rot_z = math.radians(float(values[6])),
                    angle_y = math.radians(float(values[7]))
                )
                
                chan_frames.append(frame_data)
    
    except Exception as e:
        print(f"Error reading .CHAN file: {e}")
    
    return chan_frames