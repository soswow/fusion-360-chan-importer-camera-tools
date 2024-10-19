import os
from importlib import reload
import asyncio

from adsk.core import *
from adsk.fusion import *
from ... import config
from ...lib import fusionAddInUtils as futil
from . import command

from . import store
from . import chan
from . import camera_manipulation

app = Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdCameraSlider'
CMD_NAME = 'Slide Reference Camera'
CMD_Description = ''

WORKSPACE_ID = 'FusionSolidEnvironment'
TAB_ID = 'ToolsTab'
PANEL_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_panelId'
PANEL_BESIDE_ID = 'ToolsInspectPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

IS_PROMOTED = True

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_button_resources', '')

def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    futil.add_handler(cmd_def.commandCreated, command_created)
    futil.add_handler(app.cameraChanged, camera_changed)
    futil.add_handler(ui.commandTerminated, command_terminated)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    toolbar_tab = workspace.toolbarTabs.itemById(TAB_ID)

    new_toolbarPanel_name = "Reference"
    new_toolbarPanel = toolbar_tab.toolbarPanels.add(PANEL_ID, new_toolbarPanel_name, PANEL_BESIDE_ID, False)

    control = new_toolbarPanel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED

def command_terminated(args: ApplicationCommandEventArgs):
    command.command_terminated(args)

def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    toolbar_tab = workspace.toolbarTabs.itemById(TAB_ID)
    toolbar_panel = toolbar_tab.toolbarPanels.itemById(PANEL_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if command_control:
        command_control.deleteMe()

    if command_definition:
        command_definition.deleteMe()
    
    if toolbar_panel:
        toolbar_panel.deleteMe()

def camera_changed(args: CameraEventArgs):
    command.camera_changed(args)

def command_created(args: CommandCreatedEventArgs):
    reload(command)
    reload(store)
    reload(chan)
    reload(camera_manipulation)
    command.command_created_event_handler(args)