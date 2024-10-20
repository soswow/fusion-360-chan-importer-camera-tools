import os
from importlib import reload

from adsk.core import *
from adsk.fusion import *
from ... import config
from ...lib import fusionAddInUtils as futil
from . import command

from ..chan_to_canvas import store
from ..chan_to_canvas import chan
from ..chan_to_canvas import camera_manipulation

app = Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdStickyCanvas'
CMD_NAME = 'Sticky background canvas'
CMD_Description = ''

WORKSPACE_ID = 'FusionSolidEnvironment'
TAB_ID = 'ToolsTab'
PANEL_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_panelId'
PANEL_BESIDE_ID = 'ToolsInspectPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

IS_PROMOTED = False

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_button_resources', '')
futil.log(ICON_FOLDER)

def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    futil.add_handler(cmd_def.commandCreated, command_created)
    futil.add_handler(app.cameraChanged, camera_changed)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    toolbar_tab = workspace.toolbarTabs.itemById(TAB_ID)

    toolbar_panel = toolbar_tab.toolbarPanels.itemById(PANEL_ID)

    control = toolbar_panel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED

def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if panel:
        command_control = panel.controls.itemById(CMD_ID)
        if command_control:
                command_control.deleteMe()

    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if command_definition:
        command_definition.deleteMe()

def camera_changed(args: CameraEventArgs):
    command.camera_changed(args)

def command_created(args: CommandCreatedEventArgs):
    reload(command)
    reload(store)
    reload(chan)
    reload(camera_manipulation)
    command.command_created_event_handler(args)