from adsk.core import *
from adsk.fusion import *
import adsk.core, adsk.fusion
from typing import List, Literal
import os, math

from ...lib.fusionAddInUtils import log, add_handler
from ...lib.fusionAddInUtils.general_utils import throttle
from ..chan_to_canvas import camera_manipulation
# from ..chan_to_canvas import store

app = Application.get()
ui = app.userInterface
design = Design.cast(app.activeProduct)

local_handlers = []
current_image_path = None

IMAGE_PATH_INPUT_ID = 'image_path_input_id'
IMAGE_PATH_BUTTON_INPUT_ID = 'image_path_button_input_id'
OPACITY_INPUT_ID = 'opacity_input_id'
ROTATIONZ_INPUT_ID = 'rotationz_input_id'
ROTATION_UPDOWN_INPUT_ID = 'rotation_updown_input_id'
ROTATION_SPECIAL_INPUT_ID = 'rotation_special_input_id'

IMAGE_ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image_button_resources', '')

opacity = 50
rotationz = 0
rotation_updown = 0
rotation_special = 0
initial_camera = None
manual_changing_camera_flag = False

rotationz_input: FloatSliderCommandInput = None
rotation_updown_input: FloatSliderCommandInput = None
rotation_special_input: FloatSliderCommandInput = None

def command_created_event_handler(args: CommandCreatedEventArgs):
    global current_image_path
    global opacity
    global rotationz_input
    global rotation_updown_input
    global rotation_special_input
    
    log(f'Command Created Event')
    inputs = args.command.commandInputs

    image_path_input = inputs.addTextBoxCommandInput(IMAGE_PATH_INPUT_ID, 'Image path', '', 1, False)
    if current_image_path:
        image_path_input.text = current_image_path

    image_path_button_input = inputs.addButtonRowCommandInput(IMAGE_PATH_BUTTON_INPUT_ID, 'Browse for file', True)
    image_path_button_input.listItems.add('Browse for file', False, IMAGE_ICON_FOLDER)

    opacity_input = inputs.addIntegerSliderCommandInput(OPACITY_INPUT_ID, 'Opacity', 1, 100)
    opacity_input.valueOne = opacity

    rotationz_input = inputs.addFloatSliderCommandInput(ROTATIONZ_INPUT_ID, 'Z Rotation', '', -180, 180)
    rotationz_input.valueOne = 0

    # rotation_updown_input = inputs.addFloatSliderCommandInput(ROTATION_UPDOWN_INPUT_ID, 'Up/Down Rotation','', -180, 180)
    # rotation_updown_input.valueOne = 0

    rotation_special_input = inputs.addFloatSliderCommandInput(ROTATION_SPECIAL_INPUT_ID, 'Move Y axis','', -30, 30)
    rotation_special_input.valueOne = 0

    add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

    update_initial_camera()    

def get_updown_rotation_angle(camera: Camera):
    eye = camera.eye
    target = camera.target
    camera_direction_vector = eye.vectorTo(target)
    camera_direction_vector.normalize()
    projection_to_xy = camera_direction_vector.copy()
    projection_to_xy.z = 0
    
    updown_angle = math.degrees(camera_direction_vector.angleTo(projection_to_xy))

    ## will make updown to be nagative when lower
    # projection_to_yz = camera_direction_vector.copy()
    # projection_to_yz.x = 0
    # zAxis = design.rootComponent.zConstructionAxis.geometry
    # diff_to_z =  projection_to_yz.angleTo(zAxis.direction)
    # if diff_to_z < math.pi / 2:
    #     updown_angle *= -1

    return updown_angle
    

def get_z_rotation_angle(camera: Camera):
    eye = camera.eye
    target = camera.target
    camera_direction_vector = eye.vectorTo(target)
    camera_direction_vector.normalize()
    camera_direction_vector.z = 0

    yAxis = design.rootComponent.yConstructionAxis.geometry
    z_angle_at_y =  math.degrees(camera_direction_vector.angleTo(yAxis.direction))
    xAxis = design.rootComponent.xConstructionAxis.geometry
    abs_angle = math.degrees(camera_direction_vector.angleTo(xAxis.direction ))
    z_angle_at_x = 180 - abs_angle
    if 0 < z_angle_at_y <= 90:
        z_angle_at_x = 180 + abs_angle

    return z_angle_at_x
        

def get_current_updown_rotation_angle():
    return get_updown_rotation_angle(app.activeViewport.camera)

def get_current_z_rotation_angle():
    return get_z_rotation_angle(app.activeViewport.camera)


def update_initial_camera():
    global initial_camera
    global rotationz_input
    # global rotation_updown_input
    global rotation_special_input

    view = app.activeViewport
    initial_camera = Camera.create()
    initial_camera.eye = view.camera.eye.copy()
    initial_camera.target = view.camera.target.copy()
    initial_camera.upVector = view.camera.upVector.copy()

    rotationz_input.valueOne = 0
    # rotation_updown_input.valueOne = 0
    rotation_special_input.valueOne = 0

changed_input_id = None
def command_input_changed(args: InputChangedEventArgs):
    global changed_input_id
    changed_input = args.input
    changed_input_id = changed_input.id
    
    all_inputs = Command.cast(args.firingEvent.sender).commandInputs

    if changed_input.id == IMAGE_PATH_BUTTON_INPUT_ID and isinstance(changed_input, ButtonRowCommandInput):
        button = changed_input.listItems.item(0)
        if button.isSelected:
            file_path = browse_image_file()
            if file_path:
                TextBoxCommandInput.cast(all_inputs.itemById(IMAGE_PATH_INPUT_ID)).text = file_path
            button.isSelected = False

def browse_image_file():
    # Create a file dialog to prompt the user to select a file
    file_dialog = ui.createFileDialog()
    file_dialog.title = "Select an Image file"
    file_dialog.filter = "Image Files (*.BMP;*.JPG;*.JPEG;*.GIF;*.PNG;*.TIFF);;All files (*.*)"
    file_dialog.filterIndex = 0
    
    # Show the file dialog
    dialog_result = file_dialog.showOpen()
    
    # Check if the user selected a file
    if dialog_result == DialogResults.DialogOK:
        # Get the selected file path
        return file_dialog.filename
    else:
        log("No file selected.")
        return

def command_preview(args: CommandEventArgs):
    global current_image_path
    global opacity
    global rotationz
    global rotation_updown
    global manual_changing_camera_flag

    global rotationz_input
    # global rotation_updown_input
    global rotation_special_input

    global initial_camera
    global changed_input_id

    all_inputs = args.command.commandInputs

    opacity_input: IntegerSliderCommandInput = all_inputs.itemById(OPACITY_INPUT_ID)
    opacity = opacity_input.valueOne

    beta_delta = rotation_special_input.valueOne

    # rotationz_input: FloatSliderCommandInput = all_inputs.itemById(ROTATIONZ_INPUT_ID)
    rotationz = rotationz_input.valueOne

    if changed_input_id == rotationz_input.id and beta_delta != 0:
        update_initial_camera()
        return
    
    if changed_input_id == rotation_special_input.id and rotationz != 0:
        update_initial_camera()
        return
    
    # rotation_updown_input: FloatSliderCommandInput = all_inputs.itemById(ROTATION_UPDOWN_INPUT_ID)
    rotation_updown = 0 #  rotation_updown_input.valueOne # math.degrees(-math.sin(math.radians()))

    updown_angle = math.radians(get_updown_rotation_angle(initial_camera) - rotation_updown)
    z_angle = math.radians(get_z_rotation_angle(initial_camera) + rotationz)

    # TODO add rotation and z_angle from input here
    log(f'combined z: {math.degrees(z_angle):0.2f} updown: {math.degrees(updown_angle):0.2f}')

    alpha = get_alpha(updown_angle, z_angle)
    initial_beta = get_beta(updown_angle, z_angle)
    target_beta = initial_beta + math.radians(beta_delta) # rad
    log(f'beta_delta: {beta_delta:0.2f} target_beta: {math.degrees(target_beta):0.2f} initial_beta: {math.degrees(initial_beta):0.2f}')

    target_z_angle = solve_z_angle(alpha, target_beta)
    if z_angle > math.pi:
        target_z_angle += math.pi
    # initial_z_rotation_angle = get_z_rotation_angle(initial_camera)
    extra_z_rotation = math.degrees(target_z_angle) - math.degrees(z_angle)
    log(f'targetz_z_angle: {math.degrees(target_z_angle):0.2f} initial_z: {math.degrees(z_angle):0.2f} extra_z_rotation: {extra_z_rotation:0.2f}')
    if beta_delta != 0:
        rotationz += extra_z_rotation
    
    target_updown_angle = solve_updown_angle(alpha, target_beta)
    # initial_updown_rotation_angle = get_updown_rotation_angle(initial_camera)
    extra_updown_rotation = math.degrees(target_updown_angle) - math.degrees(updown_angle)
    log(f'target_updown_angle: {math.degrees(target_updown_angle):0.2f} initial_updown_rotation_angle: {math.degrees(updown_angle):0.2f} extra_updown_rotation: {extra_updown_rotation:0.2f}')
    if beta_delta != 0:
        rotation_updown -= extra_updown_rotation
    
    eye, target, up_vector = initial_camera.eye.copy(), initial_camera.target.copy(), initial_camera.upVector.copy()
    
    rotationz_matrix = Matrix3D.create()
    zAxis = design.rootComponent.zConstructionAxis.geometry
    origin, zdirection = zAxis.origin, zAxis.direction 
    rotationz_matrix.setToRotation(math.radians(rotationz), zdirection, origin)

    eye.transformBy(rotationz_matrix)
    target.transformBy(rotationz_matrix)
    up_vector.transformBy(rotationz_matrix)

    rotation_updown_matrix = Matrix3D.create()
    right_vec = up_vector.crossProduct(target.vectorTo(eye))
    right_vec.normalize()
    rotation_updown_matrix.setToRotation(math.radians(rotation_updown), right_vec, origin)

    eye.transformBy(rotation_updown_matrix)
    target.transformBy(rotation_updown_matrix)
    up_vector.transformBy(rotation_updown_matrix)

    camera = app.activeViewport.camera
    camera.isSmoothTransition = False
    camera.eye = eye
    camera.target = target
    camera.upVector = up_vector
    
    manual_changing_camera_flag = True
    app.activeViewport.camera = camera
    manual_changing_camera_flag = False


    image_path_input: TextBoxCommandInput = all_inputs.itemById(IMAGE_PATH_INPUT_ID)
    image_path = image_path_input.text
    if image_path:
        current_image_path = image_path
        camera_manipulation.attach_background_to_camera(image_path, opacity)

    args.isValidResult = True

def command_destroy(args: CommandEventArgs):
    global local_handlers
    global rotationz_input
    local_handlers = []
    rotationz_input = None

cos, sin, tan, atan, acos, asin, sqrt = math.cos, math.sin, math.tan, math.atan, math.acos, math.asin, math.sqrt

def get_alpha(updown_angle: float, z_angle: float):
    return math.atan(-sin(updown_angle) * cos(z_angle) / sin(z_angle))

def get_beta(updown_angle: float, z_angle: float):
    return math.atan(-sin(updown_angle) * sin(z_angle) / cos(z_angle))

def solve_z_angle(alpha: float, beta: float):
    z_a = atan(sqrt(tan(beta) / tan(alpha)))
    if beta > 0:
        z_a = math.pi - z_a
    return z_a

def solve_updown_angle(alpha: float, beta: float):
    return asin(sqrt(tan(alpha) * tan(beta)))

# @throttle(0.25)
def camera_changed(args: CameraEventArgs):
    global current_image_path
    global local_handlers
    global opacity
    global rotationz
    global initial_camera
    global manual_changing_camera_flag
    global rotationz_input

    if len(local_handlers) == 0 or not rotationz_input:
        return # Command is not open
    
    updown_angle = math.radians(get_updown_rotation_angle(app.activeViewport.camera))
    z_angle = math.radians(get_z_rotation_angle(app.activeViewport.camera))

    alpha = get_alpha(updown_angle, z_angle)
    beta = get_beta(updown_angle, z_angle)
    log(f'z_a: {get_current_z_rotation_angle():.2f} ud_a: {get_current_updown_rotation_angle():.2f} alpha: {math.degrees(alpha):.2f} beta: {math.degrees(beta):.2f} solve z_a: {math.degrees(solve_z_angle(alpha, beta)):0.2f}')

    if manual_changing_camera_flag:
        return
    
    update_initial_camera()

    if not current_image_path:
        return # Image is not loaded

    delete_prev_canvas()
    camera_manipulation.attach_background_to_camera(current_image_path, opacity)

def get_root_component_canvases():
    for i in range(design.rootComponent.canvases.count):
        yield design.rootComponent.canvases.item(i)

def delete_prev_canvas():
    global current_image_path
    if not current_image_path:
        return
    
    current_canvas_name = os.path.basename(current_image_path)
    for canvas in get_root_component_canvases():
        if canvas.name == current_canvas_name:
            canvas.deleteMe()