from adsk.core import *
from adsk.fusion import *
import adsk.core, adsk.fusion
from typing import List
import os

from ...lib.fusionAddInUtils import log, add_handler
from ...lib.fusionAddInUtils.general_utils import throttle
from . import camera_manipulation
from . import store

app = Application.get()
ui = app.userInterface
design = Design.cast(app.activeProduct)

SLIDER_INPUT_ID = 'frame_slider_input'
SCALE_FACTOR_INPUT_ID = 'scale_factor_input'
CANVAS_PLACEMENT_ID = 'canvas_placement_input'
COMPONENT_SELECTOR_INPUT_ID = 'component_selector_input'
OPACITY_INPUT_ID = 'opacity_input'

CHAN_FILEPATH_TEXT_ID = 'chan_filepath_text_input'
CHAN_FILEPATH_BUTTON_ID = 'chan_filepath_button_input'

IMAGES_DIRECTORY_TEXT_ID = 'images_directory_text_input'
IMAGES_DIRECTORY_BUTTON_ID = 'images_directory_button_input'

CANVAS_PLACEMENT_FRONT = 'Front only'
CANVAS_PLACEMENT_BACK = 'Back only'
CANVAS_PLACEMENT_BOTH = 'Front and back'

CHAN_ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chan_file_resources', '')
IMAGES_ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images_directory_resources', '')

local_handlers = []
active_command_ref_component_name = None

def command_created_event_handler(args: CommandCreatedEventArgs):
    log(f'Command Created Event')

    global active_command_ref_component_name
    active_command_ref_component_name = store.get_reference_component_name()

    chan_filepath = store.get_chan_filepath() # or '/Users/sasha/Creative/Photogrammetry/models/KRGT-1 _ 1/krgt-1-1-cameras.chan'
    log(f'Stored chan filepath: {chan_filepath}')
    # store.set_chan_filepath(chan_filepath)

    images_directory = store.get_images_directory() # or '/Users/sasha/Creative/Photogrammetry/models/KRGT-1 _ 1/corrected-masked'
    log(f'Stored image directory: {images_directory}')
    # store.set_images_directory(images_directory)

    scale_factor = store.get_scale_factor()
    log(f'Scale factor: {scale_factor}')

    opacity = store.get_opacity()

    frames = store.get_chan_frames()

    app.activeViewport.visualStyle = VisualStyles.ShadedVisualStyle
    inputs = args.command.commandInputs
    
    chan_path_input = inputs.addTextBoxCommandInput(CHAN_FILEPATH_TEXT_ID, 'Nuke (.chan) file path', '', 1, False)
    if chan_filepath:
        chan_path_input.text = chan_filepath

    chan_path_buttons_input = inputs.addButtonRowCommandInput(CHAN_FILEPATH_BUTTON_ID, 'Browse for file', True)
    chan_path_buttons_input.listItems.add('Browse for file', False, CHAN_ICON_FOLDER)

    images_directory_input = inputs.addTextBoxCommandInput(IMAGES_DIRECTORY_TEXT_ID, 'Frames img directory', '', 1, False)
    if images_directory:
        images_directory_input.text = images_directory

    images_directory_buttons_input = inputs.addButtonRowCommandInput(IMAGES_DIRECTORY_BUTTON_ID, 'Choose images folder', True)
    images_directory_buttons_input.listItems.add('Browse for folder', False, IMAGES_ICON_FOLDER)

    inputs.addIntegerSliderCommandInput(SLIDER_INPUT_ID, 'Select camera', 1, len(frames) if frames else 2)

    scale_factor_input = inputs.addTextBoxCommandInput(SCALE_FACTOR_INPUT_ID, 'Scale factor', '', 1, False)
    scale_factor_input.text = str(scale_factor)

    canvas_placement_input = inputs.addDropDownCommandInput(CANVAS_PLACEMENT_ID, 'Where to put canvas?', DropDownStyles.TextListDropDownStyle)
    canvas_placement_input.listItems.add(CANVAS_PLACEMENT_BOTH, True)
    canvas_placement_input.listItems.add(CANVAS_PLACEMENT_FRONT, False)
    canvas_placement_input.listItems.add(CANVAS_PLACEMENT_BACK, False)

    opacity_input = inputs.addIntegerSliderCommandInput(OPACITY_INPUT_ID, 'Opacity', 1, 100)
    opacity_input.valueOne = opacity
    

    component_selection_input = inputs.addSelectionInput(COMPONENT_SELECTOR_INPUT_ID, 'Reference Component', 'Select a component that contains reference object')
    component_selection_input.addSelectionFilter('Occurrences')  # Only allow component occurrences to be selected
    component_selection_input.setSelectionLimits(1, 1)  # Min 1, Max 1

    # app.activeViewport.cameraChanged.add(camera_handler)
    add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    add_handler(args.command.activate, command_active, local_handlers=local_handlers)
    add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)

    add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

    for canvas in get_ref_component_canvases():
        canvas.isLightBulbOn = False


def get_component_selection_input(inputs: CommandInputs):
    return SelectionCommandInput.cast(inputs.itemById(COMPONENT_SELECTOR_INPUT_ID))

def command_active(args: CommandEventArgs):
    component = design.allComponents.itemByName(store.get_reference_component_name() or store.default_reference_component_name)
    if not component:
        log('#command_active: no component')
        return

    occurrences = design.rootComponent.occurrencesByComponent(component)

    get_component_selection_input(args.command.commandInputs).addSelection(occurrences.item(0))

def command_execute(args: CommandEventArgs):
    # Doesn't execute because we did previuew well
    pass

def command_input_changed(args: InputChangedEventArgs):
    global active_command_ref_component_name
    changed_input = args.input
    all_inputs = Command.cast(args.firingEvent.sender).commandInputs
    
    if changed_input.id == COMPONENT_SELECTOR_INPUT_ID and isinstance(changed_input, SelectionCommandInput) and changed_input.selectionCount > 0:
        occurrence: Occurrence = changed_input.selection(0).entity
        component = design.allComponents.itemById(occurrence.component.id)
        active_command_ref_component_name = component.name

    if changed_input.id == CHAN_FILEPATH_BUTTON_ID and isinstance(changed_input, ButtonRowCommandInput):
        button = changed_input.listItems.item(0)
        if button.isSelected:
            file_path = browse_chan_file()
            if file_path:
                TextBoxCommandInput.cast(all_inputs.itemById(CHAN_FILEPATH_TEXT_ID)).text = file_path
            button.isSelected = False

    if changed_input.id == IMAGES_DIRECTORY_BUTTON_ID and isinstance(changed_input, ButtonRowCommandInput):
        button = changed_input.listItems.item(0)
        if button.isSelected:
            directory = browse_images_directory()
            if directory:
                TextBoxCommandInput.cast(all_inputs.itemById(IMAGES_DIRECTORY_TEXT_ID)).text = directory
            button.isSelected = False

    # TODO wait for filepath and directory input changes (manual entry)

def command_preview(args: CommandEventArgs):
    all_inputs = args.command.commandInputs
    
    slider_input: IntegerSliderCommandInput = all_inputs.itemById(SLIDER_INPUT_ID)

    chan_path_input: TextBoxCommandInput = all_inputs.itemById(CHAN_FILEPATH_TEXT_ID)
    chan_path = chan_path_input.text
    if chan_path:
        store.set_chan_filepath(chan_path)
        slider_input = IntegerSliderCommandInput.cast(all_inputs.itemById(SLIDER_INPUT_ID))
        slider_input.maximumValue = len(store.get_chan_frames())
    
    images_directory_input: TextBoxCommandInput = all_inputs.itemById(IMAGES_DIRECTORY_TEXT_ID)
    images_directory = images_directory_input.text
    if images_directory:
        store.set_images_directory(images_directory)
        store.list_files_alphanum()
    
    scale_factor_input: TextBoxCommandInput = all_inputs.itemById(SCALE_FACTOR_INPUT_ID)
    scale_factor = scale_factor_input.text
    if scale_factor:
        store.set_scale_factor(float(scale_factor))

    canvas_placement_input: DropDownCommandInput = all_inputs.itemById(CANVAS_PLACEMENT_ID)
    canvas_placement = canvas_placement_input.selectedItem.name

    opacity_input: IntegerSliderCommandInput = all_inputs.itemById(OPACITY_INPUT_ID)
    opacity = opacity_input.valueOne
    store.set_opacity(opacity)

    component_selection_input: SelectionCommandInput = get_component_selection_input(all_inputs)
    if component_selection_input.selectionCount > 0:
        occurrence = component_selection_input.selection(0).entity
        if isinstance(occurrence, Occurrence):
            component = design.allComponents.itemById(occurrence.component.id)
            store.set_reference_component_name(component.name)
            if chan_path and images_directory:
                camera_manipulation.change_camera(slider_input.valueOne, occurrence)
                if canvas_placement == CANVAS_PLACEMENT_FRONT or canvas_placement == CANVAS_PLACEMENT_BOTH:
                    camera_manipulation.attach_background_to_chan_camera(slider_input.valueOne, component, camera_manipulation.CanvasPlacement.FRONT, 'front')
                if canvas_placement == CANVAS_PLACEMENT_BACK or canvas_placement == CANVAS_PLACEMENT_BOTH:
                    camera_manipulation.attach_background_to_chan_camera(slider_input.valueOne, component,  camera_manipulation.CanvasPlacement.BACK, 'back')
            app.activeViewport.refresh()
        else:
            ui.messageBox('It is best if you select subcomponent and not the root one')
            component_selection_input.clearSelection()

    args.isValidResult = True

def browse_chan_file():
    # Create a file dialog to prompt the user to select a file
    file_dialog = ui.createFileDialog()
    file_dialog.title = "Select a CHAN (Nuke animation) file"
    file_dialog.filter = "Text files (*.chan);;All Files (*.*)"
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
    
def browse_images_directory():
    file_dialog = ui.createFolderDialog()
    file_dialog.title = "Select a folder with images"
    current_directory = store.get_images_directory()
    if current_directory:
        file_dialog.initialDirectory = current_directory

    dialog_result = file_dialog.showDialog()
    if dialog_result == DialogResults.DialogOK:
        return file_dialog.folder
    else:
        log("No folder selected.")
        return

def command_destroy(args: CommandEventArgs):
    global local_handlers
    local_handlers = []

@throttle(0.25)
def camera_changed(args: CameraEventArgs):
    global local_handlers
    # If current command open - ignore the rules
    if len(local_handlers) > 0:
        return
    global visibile_ref_canvases
    if 0 < len(visibile_ref_canvases) <= 2:
        frame_number = get_frame_number_by_canvas_name(visibile_ref_canvases[0])
        occurrence = get_ref_occurrence()
        if not occurrence:
            log('#camera_changed: no occurence')
            return
        camera = camera_manipulation.get_camera_by_frame(frame_number, occurrence)

        if camera_manipulation.are_cameras_equal(app.activeViewport.camera, camera):
            log(f'camera matches selected canvas. keeping')
            return

        log(f'moving away from canvas, closing them down')
        for canvas in get_ref_component_canvases():
            canvas.isLightBulbOn = False

def get_ref_component_canvases():
    component = get_ref_component()
    if not component:
        log('#get_ref_component_canvases: no component')
        return
    for i in range(component.canvases.count):
        yield component.canvases.item(i)

def get_visible_ref_canvases():
    visibile_ref_canvases = []
    for canvas in get_ref_component_canvases():
        if canvas.isVisible and canvas.name.startswith('ref-frame-'):
            visibile_ref_canvases.append(canvas.name)
    visibile_ref_canvases.sort()
    return visibile_ref_canvases

visibile_ref_canvases: List[str] = []

def get_toggled_on_ref_canvases() -> List[str]:
    global visibile_ref_canvases
    currently_visible_ref_canvases = get_visible_ref_canvases()
    return [currently_visible_canvas_name for currently_visible_canvas_name in currently_visible_ref_canvases if currently_visible_canvas_name not in visibile_ref_canvases]

def get_toggled_off_canvases() -> List[str]:
    global visibile_ref_canvases
    currently_visible_canvases = get_visible_ref_canvases()
    return [prev_visible_canvas_name for prev_visible_canvas_name in visibile_ref_canvases if prev_visible_canvas_name not in currently_visible_canvases]

def get_frame_number_by_canvas_name(canvas_name: str):
    if canvas_name.startswith('ref-frame-'):
        return int(canvas_name.split('-')[2])
    
def get_ref_component():
    ref_component_name = store.get_reference_component_name()
    if ref_component_name:
        return design.allComponents.itemByName(ref_component_name)
    else:
        log('#get_ref_component: no ref component name')

def get_ref_occurrence():
    component = get_ref_component()
    if component:
        return design.rootComponent.occurrencesByComponent(component).item(0)
    else:
        log('#get_ref_occurrence: no component')

def command_terminated(args: ApplicationCommandEventArgs):
    global visibile_ref_canvases
    
    if args.commandId == 'VisibilityToggleCmd':
        toggled_on_canvases = get_toggled_on_ref_canvases()

        if len(toggled_on_canvases) == 1:
            canvas_name = toggled_on_canvases[0]
            frame_number = get_frame_number_by_canvas_name(canvas_name)
            if frame_number is not None:
                log(f'opening frame {frame_number}')
                occurrence = get_ref_occurrence()
                if occurrence:
                    camera_manipulation.change_camera(frame_number, occurrence)

    visibile_ref_canvases = get_visible_ref_canvases()

    if args.commandId == 'RestoreCameraCommand':
        log(f'{args.terminationReason}')
