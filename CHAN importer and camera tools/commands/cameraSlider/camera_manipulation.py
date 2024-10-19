import math
from enum import Enum


from adsk.core import *
from adsk.fusion import *

from ...lib.fusionAddInUtils import log

from .chan import ChanFrame
from .store import get_chan_frames, get_image_path, get_opacity, get_reference_component_name

# Add this lines at the beginning
import functools
geom_to_str = lambda x: functools.reduce(lambda a,b: f'{a}, {b}', [f'{r}: {s}' for r,s in zip("xyz", [f'{v*10:.4f} mm' for v in x.asArray()])])


app = Application.get()
design = Design.cast(app.activeProduct)

def vis_camera():
    rootComp = design.rootComponent

    # Get the active camera
    camera = app.activeViewport.camera
    eye = camera.eye
    target = camera.target
    upVector = camera.upVector

    # Create a new sketch in the root component
    sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)

    # Draw a line from eye to target
    sketch.sketchCurves.sketchLines.addByTwoPoints(eye, target)

    # Calculate the end point of the line in the direction of the upVector
    # up_point = Point3D.create(eye.x + upVector.x * 2, 
    #                             eye.y + upVector.y * 2, 
    #                             eye.z + upVector.z * 2)

    # Assuming 'sketch' is your existing Sketch object
    # Create the first line from eye to target
    eye_to_target = Vector3D.create(target.x - eye.x, target.y - eye.y, target.z - eye.z)
    eye_to_target.normalize()

    # Create the second line from eye in the direction of upVector
    up_vector = Vector3D.create(upVector.x, upVector.y, upVector.z)
    up_vector.normalize()
    up_vector_length = 2  # Set the desired length
    up_vector_end = Point3D.create(eye.x + up_vector.x * up_vector_length,
                                    eye.y + up_vector.y * up_vector_length,
                                    eye.z + up_vector.z * up_vector_length)

    # Calculate the direction for the perpendicular line
    # Using the components of the vectors to create a perpendicular vector
    perpendicular_vector = Vector3D.create(
        eye_to_target.y * up_vector.z - eye_to_target.z * up_vector.y,
        eye_to_target.z * up_vector.x - eye_to_target.x * up_vector.z,
        eye_to_target.x * up_vector.y - eye_to_target.y * up_vector.x
    )
    perpendicular_vector.normalize()
    perpendicular_length = 2  # Set the desired length
    perpendicular_end = Point3D.create(eye.x + perpendicular_vector.x * perpendicular_length,
                                        eye.y + perpendicular_vector.y * perpendicular_length,
                                        eye.z + perpendicular_vector.z * perpendicular_length)

    # Add the lines to the sketch
    sketch.sketchCurves.sketchLines.addByTwoPoints(eye, target)  # Line from eye to target
    sketch.sketchCurves.sketchLines.addByTwoPoints(eye, up_vector_end)  # Line in the direction of upVector
    sketch.sketchCurves.sketchLines.addByTwoPoints(eye, perpendicular_end)  

def calculate_target_point(camera: ChanFrame, distance: float = 50.0):
    # Extract Euler angles in radians (pitch, yaw, roll)
    pitch, yaw, roll = camera.rotation_euler

    # Create an identity matrix
    rotation_matrix = Matrix3D.create()

    # Apply pitch (rotation around X-axis)
    rotation_x_matrix = Matrix3D.create()
    rotation_x_matrix.setToRotation(pitch, Vector3D.create(1, 0, 0), camera.location)
    rotation_matrix.transformBy(rotation_x_matrix)

    # Apply yaw (rotation around Y-axis)
    rotation_y_matrix = Matrix3D.create()
    rotation_y_matrix.setToRotation(yaw, Vector3D.create(0, 1, 0), camera.location)
    rotation_matrix.transformBy(rotation_y_matrix)

    # Apply roll (rotation around Z-axis)
    rotation_z_matrix = Matrix3D.create()
    rotation_z_matrix.setToRotation(roll, Vector3D.create(0, 0, 1), camera.location)
    rotation_matrix.transformBy(rotation_z_matrix)

    # Extract the final coordinate system from the rotation matrix
    origin, xAxis, yAxis, zAxis = rotation_matrix.getAsCoordinateSystem()

    # Scale the zAxis by the desired distance (in front of the camera)
    zAxis.scaleBy(-distance)  # negative Z-axis as forward direction

    # Calculate the target point by adding the scaled vector to the camera's position
    target_x = camera.location.x + zAxis.x
    target_y = camera.location.y + zAxis.y
    target_z = camera.location.z + zAxis.z
    
    return Point3D.create(target_x, target_y, target_z)

def get_camera_by_frame(frameNumber: int, context_occurrence: Occurrence):
    frames = get_chan_frames()
    if not frames:
        log('#get_camera_by_frame: no frames')
        return
    frame = frames[frameNumber-1]
    target = calculate_target_point(frame)
    eye = frame.location.copy()
    fov = frame.angle_y

    up_vector = Vector3D.create(0, 1, 0)
    rotation_z_matrix = Matrix3D.create()
    #TODO Fix that problem for some shots
    # log(f'{frame.rotation_euler[2]} rad, {math.degrees(frame.rotation_euler[2])} deg')
    log(f'frame #{frameNumber} pos: {frame.location.x} {frame.location.y} angle: {math.degrees(frame.rotation_euler[0])} {math.degrees(frame.rotation_euler[1])} {math.degrees(frame.rotation_euler[2])}')
    rotation_z_matrix.setToRotation(frame.rotation_euler[2], Vector3D.create(0, 0, 1), eye)
    up_vector.transformBy(rotation_z_matrix)
    if frame.rotation_euler[0] > math.radians(90):
        up_vector.scaleBy(-1)

    target.transformBy(context_occurrence.transform2)
    eye.transformBy(context_occurrence.transform2)
    up_vector.transformBy(context_occurrence.transform2)

    # Making sure up-vector is actually perpendicular to plane of the camera
    # new_up_vector = up_vector.copy()
    normal = target.vectorTo(eye)
    normal.normalize()
    right_vec = up_vector.crossProduct(normal)
    normal.normalize()
    new_up_vector = normal.crossProduct(right_vec)
    new_up_vector.normalize()

    
    cam = Camera.create()
    cam.cameraType = CameraTypes.PerspectiveCameraType
    cam.perspectiveAngle = fov
    cam.isSmoothTransition = False
    cam.eye = eye
    cam.target = target
    cam.upVector = new_up_vector
    return cam

def change_camera(frameNumber: int, context_occurrence: Occurrence):
    view = app.activeViewport
    if view.camera.cameraType != CameraTypes.PerspectiveCameraType:
        app.userInterface.messageBox('Only works with Perspective Camera')

    camera = get_camera_by_frame(frameNumber, context_occurrence)
    if not camera:
        log('#change_camera: no camera')
        return
    view.camera = camera
    view.refresh()

def farthest_mesh_corner_from_camera_distance():
    max_distance = -1  # Start with a negative value to ensure the first comparison is valid

    # Iterate through all corners and calculate the distance to the camera eye
    corners = mesh_bounding_box_corners()
    for corner in corners:
        distance = corner.distanceTo(app.activeViewport.camera.eye)
        
        # If this distance is greater than the current max_distance, update max_distance and farthest_corner
        if distance > max_distance:
            max_distance = distance
    return max_distance

def mesh_bounding_box_corners():
    component = design.allComponents.itemByName(get_reference_component_name())
    occurrence = design.rootComponent.occurrencesByComponent(component).item(0)
    mesh = component.meshBodies.item(0)
    
    bounding_box = mesh.boundingBox

    # Retrieve minPoint and maxPoint
    min_point = bounding_box.minPoint
    max_point = bounding_box.maxPoint

    # Generate all 8 corners of the bounding box using min and max points
    corners = [
        Point3D.create(min_point.x, min_point.y, min_point.z),
        Point3D.create(max_point.x, min_point.y, min_point.z),
        Point3D.create(min_point.x, max_point.y, min_point.z),
        Point3D.create(max_point.x, max_point.y, min_point.z),
        Point3D.create(min_point.x, min_point.y, max_point.z),
        Point3D.create(max_point.x, min_point.y, max_point.z),
        Point3D.create(min_point.x, max_point.y, max_point.z),
        Point3D.create(max_point.x, max_point.y, max_point.z),
    ]

    for corner in corners:
        corner.transformBy(occurrence.transform2)

    #     point_input = design.rootComponent.constructionPoints.createInput()
    #     point_input.setByPoint(corner)
    #     design.rootComponent.constructionPoints.add(point_input)

    return corners


class CanvasPlacement(Enum):
    FRONT = 1
    BACK = 2

def attach_background_to_camera(frame_number: int, component: Component, placement: CanvasPlacement, postfix: str = "" ):
    context_occurrence = design.rootComponent.occurrencesByComponent(component).item(0)
    context_occurrence.activate()
    image_path = get_image_path(frame_number)
    if not image_path:
        log('#attach_background_to_camera: no image path')
        return
    # log(f'filepath: {image_path}')
    view = app.activeViewport
    eye = view.camera.eye.copy()
    target = view.camera.target.copy()
    up_vector = view.camera.upVector.copy()

    transform_matrix = context_occurrence.transform2
    transform_matrix.invert()

    target.transformBy(transform_matrix)
    eye.transformBy(transform_matrix)
    up_vector.transformBy(transform_matrix)

    fov = view.camera.perspectiveAngle

    up_vector.normalize()

    normal = Vector3D.create(target.x - eye.x, target.y - eye.y, target.z - eye.z)
    normal.normalize()

    distance = 10 if placement == CanvasPlacement.FRONT else farthest_mesh_corner_from_camera_distance()

    new_target = Point3D.create(eye.x + normal.x * distance,
                                    eye.y + normal.y * distance,
                                    eye.z + normal.z * distance)
    
    rightVec: Vector3D = up_vector.crossProduct(target.vectorTo(eye))
    rightVec.normalize()

    plane = Plane.createUsingDirections(
        new_target,
        rightVec,
        up_vector,
    )
    
    canvas_height = 2 * (distance * math.tan(fov/2))

    # imagePath = "/Users/sasha/Documents/test_image_7000x4200.png"
    canvas_input = component.canvases.createInput(image_path, plane)
    canvas_input.imageFilename = image_path
    canvas_input.isDisplayedThrough = True
    canvas_input.opacity = get_opacity()
    
    current_transform_array = canvas_input.transform.asArray()
    initial_canvas_height = current_transform_array[4]
    scale_factor = canvas_height / initial_canvas_height

    # | scale_x     shear_x     translate_x |
    # | shear_y     scale_y     translate_y |
    # | 0.0         0.0         1.0         |

    scaled_transform_array = [
        current_transform_array[0] * scale_factor,   # Scale X
        current_transform_array[1],                  # Shear X (0)
        current_transform_array[2] * scale_factor,   # Translate X
        current_transform_array[3],                  # Shear Y (0)
        current_transform_array[4] * scale_factor,   # Scale Y
        current_transform_array[5] * scale_factor,   # Translate Y
        current_transform_array[6],                   # Homogeneous coordinate (0)
        current_transform_array[7],                   # Homogeneous coordinate (0)
        current_transform_array[8]                    # Homogeneous coordinate (1)
    ]

    new_transform = Matrix2D.create()
    new_transform.setWithArray(scaled_transform_array)

    canvas_input.transform = new_transform
    
    canvas = component.canvases.add(canvas_input)
    name = f'ref-frame-{frame_number}'
    if postfix:
        name += f'-{postfix}'
    canvas.name = name

    # filename_with_ext = os.path.basename(image_path)
    # filename_without_ext = os.path.splitext(filename_with_ext)[0]
    # design.namedViews.add(app.activeViewport.camera, filename_without_ext)

    # log(f'Canvas added to {component.name} where there are {component.canvases.count} of them already.')

def are_cameras_equal(cameraA: Camera, cameraB: Camera):
    return cameraA.eye.isEqualTo(cameraB.eye) and \
            cameraA.target.isEqualTo(cameraB.target) and \
            cameraA.upVector.isEqualTo(cameraB.upVector) and \
            cameraA.perspectiveAngle == cameraB.perspectiveAngle