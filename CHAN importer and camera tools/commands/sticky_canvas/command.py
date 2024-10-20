from adsk.core import *
from adsk.fusion import *
import adsk.core, adsk.fusion
from typing import List
import os

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

IMAGE_ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image_button_resources', '')

def command_created_event_handler(args: CommandCreatedEventArgs):
    global current_image_path
    log(f'Command Created Event')
    inputs = args.command.commandInputs

    image_path_input = inputs.addTextBoxCommandInput(IMAGE_PATH_INPUT_ID, 'Image path', '', 1, False)
    if current_image_path:
        image_path_input.text = current_image_path

    image_path_button_input = inputs.addButtonRowCommandInput(IMAGE_PATH_BUTTON_INPUT_ID, 'Browse for file', True)
    image_path_button_input.listItems.add('Browse for file', False, IMAGE_ICON_FOLDER)

    add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def command_input_changed(args: InputChangedEventArgs):
    changed_input = args.input
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
    all_inputs = args.command.commandInputs

    image_path_input: TextBoxCommandInput = all_inputs.itemById(IMAGE_PATH_INPUT_ID)
    image_path = image_path_input.text
    if image_path:
        current_image_path = image_path
        camera_manipulation.attach_background_to_camera(image_path, 100, 50)

    args.isValidResult = True

def command_destroy(args: CommandEventArgs):
    global local_handlers
    local_handlers = []

def camera_changed(args: CameraEventArgs):
    global current_image_path
    global local_handlers
    if not current_image_path or len(local_handlers) == 0:
        return

    delete_prev_canvas()
    camera_manipulation.attach_background_to_camera(current_image_path, 100, 50)

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